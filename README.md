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
yap_output = call_api(text, url)
for _, sent in yap_output:
    df = parse_yap_output(sent)
    print(run(df))
```

