import streamlit as st
from src.utils import parse_yap_output, call_api
from src.converter import convert_dep_tree_to_ud

from spacy import displacy
import base64

st.title("Convert YAP's SPMRL output to UD")

url = 'http://localhost:8000/yap/heb/joint'  # change this if you refer to a remote YAP server


def convert_to_displacy_format(df):
    displacy_style = {
        "collapse_punct": False,
        "collapse_phrases": False,
        "compact": False,
        "distance": 100,
        "word_spacing": 10,
        "arrow_stroke": 0.5,
        "font": "IBM Plex Mono,monospace",
        "direction": "rtl"
    }

    displacy_input = {"words": [], "arcs": []}
    for i, row in df.iterrows():
        displacy_input["words"].append({"text": row["FORM"], "tag": row["UPOS"]})
        if row["DEPREL"] != "ROOT":
            start = int(row["ID"])-1
            end = int(row["HEAD"])-1
            direction = "left" if start < end else "right"
            displacy_input["arcs"].append({"start": start, "end": end, "label": row["DEPREL"], "dir": direction})
    svg_tree = displacy.render(displacy_input, options=displacy_style, manual=True, style='dep')

    # b64 = base64.b64encode(svg_tree.encode('utf-8')).decode("utf-8")
    # svg_tree = r'<img src="data:image/svg+xml;base64,%s"/>' % b64

    return svg_tree


if __name__ == "__main__":
    text = st.text_input("sentence goes here")
    content = call_api(text)
    spmrl = parse_yap_output(content)

    dep_svg_spmrl = convert_to_displacy_format(spmrl)
    st.image(dep_svg_spmrl, use_column_width="never")

    ud = convert_dep_tree_to_ud(spmrl)
    dep_svg_ud = convert_to_displacy_format(ud)
    st.image(dep_svg_ud, use_column_width="never")
