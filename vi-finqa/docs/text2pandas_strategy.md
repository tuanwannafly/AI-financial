# Text-to-Pandas strategy

## Operation frequency (gold + synthetic queries)

`py -m src.text2pandas.analyze_operations` on 6226 gold+synthetic queries:

| op | n |
|---|---|
| lookup_simple (iloc) | 6226 |
| filter_year | 4152 |
| ratio | 1660 |
| pct_change | 408 |
| groupby / merge | 0 |

No groupby/merge in gold templates (values pre-joined on evidence CSV).

## Serializers
Four functions in `src/text2pandas/serialize.py`. Oracle template generator **ignores** serializer text → equal 51.25% first-try; default markdown.
