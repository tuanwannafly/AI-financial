import json
from pathlib import Path

with open('submissions/questions.jsonl', encoding='utf-8') as f:
    questions = [json.loads(line) for line in f if line.strip()]
print('Total questions:', len(questions))
unk_count = sum(1 for q in questions if 'unk|0' in q.get('relevant_tables', []))
zero_answer = sum(1 for q in questions if q.get('answer') == 0.0)
print('Questions with unk|0 in relevant_tables:', unk_count)
print('Questions with answer==0.0:', zero_answer)
both = sum(1 for q in questions if 'unk|0' in q.get('relevant_tables', []) and q.get('answer') == 0.0)
print('Both unk and zero answer:', both)
neither = sum(1 for q in questions if not ('unk|0' in q.get('relevant_tables', [])) and q.get('answer') != 0.0)
print('Neither unk nor zero:', neither)
print()

# Now compare to our pack
with open('submissions/public_506/_pack_v2/submission.json', encoding='utf-8') as f:
    submission = json.load(f)
print('Submission entries:', len(submission))

# Check our pack's zero answers
our_zero = sum(1 for s in submission if s.get('answer') == 0.0)
print('Our submission entries with answer==0.0:', our_zero)

# Check our pack's queries that use '0.0'
our_zero_query = sum(1 for s in submission if s.get('pandas_query') == '0.0')
print('Our queries that are just "0.0":', our_zero_query)

# Number of CSV files
import os
csv_dir = 'submissions/public_506/_pack_v2/data'
print('Number of CSV files:', len([f for f in os.listdir(csv_dir) if f.endswith('.csv')]))