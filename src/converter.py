import pandas as pd
import networkx as nx
import json
from collections import defaultdict
import logging
from src.utils import call_api, parse_yap_output

logger = logging.getLogger()

try:
    with open('conversion_map.json', 'r') as f:
        CONVERSION_TABLE = json.load(f)
except FileNotFoundError:
    with open('src/conversion_map.json', 'r') as f:
        CONVERSION_TABLE = json.load(f)

PRONOUNS = CONVERSION_TABLE["pronouns"]
POS = CONVERSION_TABLE["basic_pos"]
LABELS = CONVERSION_TABLE["basic_labels"]
FEATURES = CONVERSION_TABLE["basic_features"]
ENTIRE_LINE = CONVERSION_TABLE["entire_line_pos_conversion"]


def update_label(graph, node_idx, parent_idx, new_label):
    graph.nodes[node_idx]["arc_label"]["new"] = new_label
    graph.nodes[node_idx]["parent"] = parent_idx
    graph.add_edge(parent_idx, node_idx, label=new_label)


def reorganize_conjunction(graph, conj_node_idx, conj_node, conj_parent_idx, conjuncts):
    if conj_parent_idx:
        update_label(graph=graph, node_idx=conjuncts[0], parent_idx=conj_parent_idx, new_label=conj_node["arc_label"]["new"])
        graph.remove_edge(conj_parent_idx, conj_node_idx)
        graph.remove_edge(conj_node_idx, conjuncts[0])
        for conjunct in conjuncts[1:]:
            graph.remove_edge(conj_node_idx, conjunct)
            # this should be conj also in SPMRL but there are occasional errors:
            update_label(graph, conjunct, conjuncts[0], "conj")
        update_label(graph, conj_node_idx, conjuncts[-1], "cc")
    else:
        new_root = 0
        outlier = conjuncts[0]
        for i, c in enumerate(conjuncts):
            graph.remove_edge(conj_node_idx, c)
            if not new_root and graph.nodes[c]["pos"]["new"] == "VERB":
                new_root = c
                # graph.add_edge(c, outlier, label=graph.nodes[outlier]["arc_label"]["new"])
                graph.nodes[c]["arc_label"]["new"] = "ROOT"
                graph.nodes[c]["parent"] = -1
            else:
                update_label(graph, node_idx=c, parent_idx=new_root, new_label="conj")
        update_label(graph, conj_node_idx, conjuncts[-1], new_label="cc")
        update_label(graph, outlier, new_root, new_label=graph.nodes[outlier]["arc_label"]["new"])

    return graph


def reverse_arc_direction(graph, node_idx, self_label, marker_label):
    parents = list(graph.predecessors(node_idx))  # idx of prepmod
    try:
        grandparent = list(graph.predecessors(parents[0]))[0]  # idx of head
    except:
        sentence = " ".join([graph.nodes[n]["form"]["old"] for n in graph.nodes])
        node_word = graph.nodes[node_idx]["form"]["old"]
        parent_label = graph.nodes[parents[0]]["arc_label"]["new"]

        logger.warning(f"The parse for sentence {sentence} may be wrong. "
                       f"The parent of {node_word} should be '{marker_label}' but it's '{parent_label}'. "
                       f"Aborting edges swap.")
        return graph
    graph.remove_edge(grandparent, parents[0])
    graph.remove_edge(parents[0], node_idx)
    update_label(graph=graph, node_idx=node_idx, parent_idx=grandparent, new_label=self_label)
    update_label(graph=graph, node_idx=parents[0], parent_idx=node_idx, new_label=marker_label)
    return graph


def convert_labels(graph, node_idx, node, parents):
    children = list(graph.successors(node_idx))
    entire_row_changes = CONVERSION_TABLE["labels_with_features_changed"]
    old_label = node['arc_label']['old']
    parent = parents[0] if parents else 0

    if not node["arc_label"]["new"]:
        if old_label in LABELS.keys():
            update_label(graph, node_idx, parent, LABELS[old_label])

        elif old_label in entire_row_changes.keys():
            update_label(graph, node_idx, parent, entire_row_changes[old_label]["label"])
            node["pos"]["new"] = entire_row_changes[old_label]["pos"]
            node["features"]["new"] = compose_features(old_label, node, entire_row_changes)
    if node["pos"]["old"] == "CONJ":  # the cc can by of any label.
        graph = reorganize_conjunction(graph, node_idx, node, parent, children)
    to_reverse = [("obl", "case"), ("ccomp", "mark"), ("advcl", "mark"), ("acl:relcl", "mark"), ("obj", "case:acc")]
    for head, child in to_reverse:
        if node["arc_label"]["new"] == head:
            graph = reverse_arc_direction(graph, node_idx, head, marker_label=child)

    if old_label == "neg":
        node["arc_label"]["new"] = "det" if graph.nodes[parent]["pos"]["old"] == "NN" else "advmod"

    return graph


def base_features_conversion(old_features):
    feats = old_features.split("|")
    if all(f in feats for f in ["gen=F", "gen=M"]):
        # otherwise both Gender=Fem and Gender=Masc will be added
        feats.append("gen=F|gen=M")
        feats.remove("gen=F")
        feats.remove("gen=M")
    current_feats = [f for f in feats if not f.startswith("suf_")]
    suffix_feats = [f.replace("suf_", "") for f in feats if f.startswith("suf_")]
    old_features = "|".join(current_feats)
    for feature in current_feats:
        if feature:
            old_features = old_features.replace(feature, FEATURES[feature])
    return old_features, suffix_feats


def convert_features(graph, node_idx, node):
    old_features = node["features"]["old"]
    converted_features, suffix_feats = base_features_conversion(old_features)
    if not node["features"]["new"]:
        if suffix_feats:
            if node["pos"]["old"] == 'NN':
                node["lemma"]["new"] = '_'
                node["pos"]["new"] = 'NOUN'
                node["features"]["new"] = f"Definite=Def|{converted_features}"
            else:
                node["features"]["new"] = converted_features
        else:
            node["features"]["new"] = converted_features
            node = specific_feats_conversions(node)
            if node["pos"]["new"] == "PRON":
                if node["lemma"]["old"] == "עצמו":
                    if node["arc_label"]["old"] == "nn":
                        node["features"]["new"] += f"{node['features']['new']}|PronType=Emp|Reflex=Yes" if node["features"]["new"] else "PronType=Emp|Reflex=Yes"
                    else:
                        node["features"]["new"] += f"{node['features']['new']}|PronType=Prs|Reflex=Yes" if node["features"]["new"] else "PronType=Emp|Reflex=Prs"
                elif "PronType" not in node["features"]["new"]:
                    for prontype, lemmas in CONVERSION_TABLE["determiner_types"].items():
                        if node["lemma"]["old"] in lemmas:
                            node["features"]["new"] = f"{node['features']['new']}|PronType=Emp" if node["features"]["new"] else prontype
    return graph


def specific_feats_conversions(node):
    if node["arc_label"]["old"] == "posspmod":
        node["features"]["new"] = 'Case=Gen'
    elif node['pos']['old'] == "PRP":
        if node['arc_label']['old'] == "subj":
            node["features"]["new"] += "|PronType=Prs"
        elif node['arc_label']['old'] == "det":
            node["features"]["new"] += "|PronType=Dem"
    return node


def convert_pos(graph, node_idx, node):
    old_pos = node['pos']['old']
    if old_pos in POS.keys():
        node['pos']['new'] = POS[old_pos]
    elif old_pos in ENTIRE_LINE.keys():
        node['pos']['new'] = ENTIRE_LINE[old_pos]["pos"]
        node['features']['new'] = compose_features(old_pos, node, ENTIRE_LINE)
        if ENTIRE_LINE[old_pos].get("arc_label"):
            node['arc_label']['new'] = ENTIRE_LINE[old_pos]["arc_label"]
        concat = ENTIRE_LINE[old_pos].get("concat")
        if concat == "before":
            node['form']['new'] = f"_{node['form']['old']}"
        elif concat == "after":
            node['form']['new'] = f"{node['form']['old']}_"
    elif old_pos == 'S_PRN':
        if graph.nodes[node_idx-1]['pos']['old'] == 'AT':
            graph.nodes[node_idx - 1]["features"]["new"] = 'Case=Acc' # probably redundant
        elif graph.nodes[node_idx-1]['lemma']['old'] == 'של':
            graph.nodes[node_idx - 1]["features"]["new"] = 'Case=Gen'
        elif graph.nodes[node_idx-1]['pos']['old'] == 'IN':
            graph.nodes[node_idx - 1]["features"]["new"] = '_'
        node['form']['new'] = "_" + node['lemma']['old']
        node['pos']['new'] = 'PRON'
    elif old_pos == 'CC' and node['lemma']['old'] == 'כי':
        node['pos']['new'] = 'SCONJ'
    return graph


def compose_features(key, node, map):
    replacement_feats = map[key]["feats"]
    new_base_features, suffix_feats = base_features_conversion(node['features']['old'])
    if replacement_feats["method"] == "+feats+":
        features = f"{replacement_feats['addition'][0]}|{new_base_features}|{replacement_feats['addition'][1]}"
    elif replacement_feats["method"] == "feats+":
        if node['features']['old']:
            features = f"{new_base_features}|{replacement_feats['addition']}"
        else:
            features = replacement_feats['addition']
    elif replacement_feats["method"] == "+feats":
        features = f"{replacement_feats['addition']}|{new_base_features}"
    else:
        features = replacement_feats["addition"]
    return features


def convert_graph(graph: nx.DiGraph) -> nx.DiGraph:
    for node_idx in graph.nodes:
        node = graph.nodes[node_idx]
        parents = list(graph.predecessors(node_idx))
        graph = convert_pos(graph, node_idx, node)
        graph = convert_features(graph, node_idx, node)
        graph = convert_labels(graph, node_idx, node, parents)
        for att in ["form", "pos", "lemma", "arc_label"]:
            if not node[att]["new"]:
                node[att]["new"] = node[att]["old"]
    return graph


def add_functional_nodes_if_necessary(graph, node_idx):
    node = graph.nodes[node_idx]
    pos = node["pos"]["old"]
    features = node["features"]["old"]
    offset = 0
    if "suf_" in features:
        suffix_feats = "|".join([x for x in features.split("|") if 'suf' in x])
        clean_suffix_feats, _ = base_features_conversion(suffix_feats.replace("suf_", ""))
        if pos in ["NN", "NN_S_PP", "S_PP"]:
            graph.add_node(
                node_idx+1,
                form={"new": "_של_", "old": ""},
                pos={"new": "ADP", "old": ""},
                lemma={"new": "_של_", "old": ""},
                features={"new": "_", "old": features},
                arc_label={"new": "case:gen", "old": "case:gen"},
                parent=node_idx+2,
            )
            graph.add_node(
                node_idx+2,
                form={"new": PRONOUNS[suffix_feats], "old": ""},
                pos={"new": "PRON", "old": ""},
                lemma={"new": "הוא", "old": ""},
                features={"new": f"Case=Gen|{clean_suffix_feats}|PronType=Prs", "old": ""},
                arc_label={"new": "nmod:poss", "old": "nmod:poss"},
                parent=node_idx,
            )
            offset += 2
        elif pos in ["DTT", "DT"]: # כולנו
            # add another row of הוא
            graph.add_node(
                node_idx+1,
                form={"new": PRONOUNS[suffix_feats], "old": ""},
                pos={"new": "PRON", "old": ""},
                lemma={"new": "הוא", "old": ""},
                features={"new": f"Case=Gen|{clean_suffix_feats}|PronType=Prs", "old": features},
                arc_label={"new": "nmod:poss", "old": "nmod:poss"},
                parent=node_idx,
            )
            offset += 1
    return offset


def add_edges(graph, parents_traceback):
    for x in range(len(graph.nodes)):
        node = graph.nodes[x]
        if node["parent"] == -1:
            continue
        elif node["parent"] in parents_traceback.keys():
            parent = parents_traceback[node["parent"]]
            graph.add_edge(u_of_edge=parent, v_of_edge=x, label=node["arc_label"]["old"])
        else:
            graph.add_edge(u_of_edge=node["parent"], v_of_edge=x, label=node["arc_label"]["old"])


def add_nodes(graph, dep_tree):
    offset = 0
    parents_traceback = defaultdict(int)
    for i, row in dep_tree.iterrows():
        parent = int(row["HEAD"])-1
        if parent >= 0 and offset > 0:  # do not add offset if parent is 0 (root)
            parents_traceback[parent] = parent + offset
        graph.add_node(i+offset,
                       form={"new": "", "old": row["FORM"]},
                       pos={"new": "", "old": row['XPOS']},
                       lemma={"new": "", "old": row['LEMMA']},
                       features={"new": "", "old": row["FEATS"]},
                       arc_label={"new": "", "old": row["DEPREL"]},
                       parent=parent,
                       )
        offset += add_functional_nodes_if_necessary(graph, i+offset)
    return parents_traceback


def convert_sentence_to_graph(dep_tree) -> nx.DiGraph:
    graph = nx.DiGraph()
    parents_traceback = add_nodes(graph, dep_tree)
    add_edges(graph, parents_traceback)
    convert_graph(graph)
    return graph


def run(dep_tree: pd.DataFrame) -> pd.DataFrame:
    graph = convert_sentence_to_graph(dep_tree)
    nodelist = list(graph.nodes(data=True))
    df = pd.DataFrame(columns=["ID", "FORM", "LEMMA", "XPOS", "UPOS", "FEATS", "HEAD", "DEPREL"])
    for node in nodelist:
        df = df.append(
            {
                "ID": str(node[0]+1),
                "FORM": node[1]["form"]["new"],
                "LEMMA": node[1]["lemma"]["new"],
                "XPOS": node[1]["pos"]["old"],
                "UPOS": node[1]["pos"]["new"],
                "FEATS":node[1]["features"]["new"],
                "HEAD": str(node[1]["parent"]+1),
                "DEPREL": node[1]["arc_label"]["new"],
        }, ignore_index=True)
    return df


if __name__ == '__main__':
    url = 'http://127.0.0.1:8000'
    text = 'אכלת פלפל? שתה מיץ.'
    yap_output = call_api(text, url)
    for _, sent in yap_output:
        df = parse_yap_output(sent)
        parsed_sent = run(df)
        print(type(parsed_sent), parsed_sent)


