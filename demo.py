import streamlit as st
from src.utils import parse_yap_output, call_api
from src.converter import convert

from spacy import displacy
import base64


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
        tag = f'{row["UPOS"]}/{row["ENTS"]}' if row["ENTS"] else row["UPOS"]
        displacy_input["words"].append({"text": row["FORM"], "tag": tag})

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
    url = 'http://localhost'  # change this if you refer to a remote YAP server
    with st.sidebar:
        st.title("Convert YAP's SPMRL output to UD")
        st.markdown("""
        <style>
        textarea {
          unicode-bidi:bidi-override;
          direction: RTL;
        }
        </style>
            """, unsafe_allow_html=True)
        text = st.text_area("", placeholder="גנן גידל דגן בגן")
        ner_method = st.selectbox('NER?', ('Only YAP', 'morph_hybrid', 'multi_align_hybrid'))
        button = st.button('parse text')
    if button:
        st.header("Dependency Trees")
        nemo = True
        if ner_method == "Only YAP":
            ner_method = "yap/heb/joint"
            nemo = False
        for sentence, content, ents in call_api(text, url, method=ner_method, use_nemo=nemo):
            st.subheader(sentence)
            st.write("SPMRL: ")
            spmrl = None
            try:
                spmrl = parse_yap_output(content, ents)
                # st.dataframe(spmrl)
                dep_svg_spmrl = convert_to_displacy_format(spmrl)

                st.write(dep_svg_spmrl, unsafe_allow_html=True)
                if not dep_svg_spmrl:
                    st.error(f"Could not parse the sentence {sentence} with YAP. Try another method (e.g. morph_hybrid)")
            except:
                st.error(f"Could not parse the sentence {sentence} with YAP. Try another method (e.g. morph_hybrid)")
            if spmrl is not None:
                st.write("UD: ")
                ud = convert(spmrl)
                # st.dataframe(ud, width=20000)
                dep_svg_ud = convert_to_displacy_format(ud)
                st.write(dep_svg_ud, unsafe_allow_html=True)



