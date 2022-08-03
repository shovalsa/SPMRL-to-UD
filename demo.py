import streamlit as st
from src.utils import parse_yap_output, call_api
from src.converter import convert_dep_tree_to_ud

import spacy
from spacy import displacy
import base64
from io import StringIO



url = 'http://localhost:8000/yap/heb/joint'  # change this if you refer to a remote YAP server


def convert_to_displacy_format(df):
    displacy_style = {
        "collapse_punct": False,
        "collapse_phrases": False,
        "compact": False,
        "distance": 100,
        # "word_spacing": 10,
        "arrow_stroke": 0.5,
        "font": "IBM Plex Mono,monospace",
        "direction": "rtl"
    }

    displacy_input = {"words": [], "arcs": []}
    for i, row in df.iterrows():
        displacy_input["words"].append({"text": row["FORM"], "tag": row["UPOS"]})

        if row["DEPREL"] != "ROOT":
            head = int(row["HEAD"])-1
            dependent = int(row["ID"])-1
            if head < dependent:
                displacy_input["arcs"].append({"start": head, "end": dependent, "label": row["DEPREL"], "dir": "right"})
            else:
                displacy_input["arcs"].append({"start": dependent, "end": head, "label": row["DEPREL"], "dir": "left"})

    svg_tree = displacy.render(displacy_input, options=displacy_style, manual=True, style='dep', page=False)

    b64 = base64.b64encode(svg_tree.encode('utf-8')).decode("utf-8")
    svg_tree = r'<img src="data:image/svg+xml;base64,%s"/>' % b64
    return svg_tree


if __name__ == "__main__":
    with st.sidebar:
        st.title("Convert YAP's SPMRL output to UD")
        text = st.text_area("", placeholder="גנן גידל דגן בגן")
        button = st.button('parse text')
    if button:
        st.header("Dependency Trees")
        for sentence, content in call_api(text):
            st.subheader(sentence)
            st.write("SPMRL: ")
            spmrl = None
            try:
                spmrl = parse_yap_output(content)

                dep_svg_spmrl = convert_to_displacy_format(spmrl)

                st.write(dep_svg_spmrl, unsafe_allow_html=True)
            except:
                error = f"Could not parse the sentence {sentence} with YAP."
            if spmrl is not None:
                st.write("UD: ")
                try:
                    ud = convert_dep_tree_to_ud(spmrl)
                    dep_svg_ud = convert_to_displacy_format(ud)
                    st.write(dep_svg_ud, unsafe_allow_html=True)
                except Exception as e:
                    st.write(f"Could not convert sentence {sentence} to UD. {e}")


