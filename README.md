# SPMRL-to-UD
converts [YAP](https://github.com/OnlpLab/yap)'s output from the SPMRL scheme to UD v2.


## Useful links
1. [UD general guidelines](https://universaldependencies.org/guidelines.html)
2. [Hebrew treebank](https://github.com/UniversalDependencies/UD_Hebrew-HTB/tree/master)
3. [Hebrew specific guidelines](https://universaldependencies.org/he/index.html)

## How to Use
First, install dependencies with `pip install -r requirements.txt`.
Run a YAP server locally. If it runs remotely, modify the url in `converter.py` or `demo.py`.

To run the demo, simply run:
```
$ streamlit run demo.py
```
Otherwise, embed this in your python code:
```
from src.utils import call_api, parse_yap_output
from src.converter import run

text = 'אכלת פלפל? שתה מיץ.' # or any text you wish
url = ... # your YAP/NEMO server address (without port)
method = <"yap/heb/joint" / "multi_align_hybrid" / "morph_hybrid">
for sentence, content, ents in call_api(text, url, use_nemo=<False/True>, method=method):
    spmrl = parse_yap_output(content, ents)
    ud = convert(spmrl)
```

