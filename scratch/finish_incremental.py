import sys, json
from pathlib import Path
from graphify.build import build_merge, build_from_json
from graphify.detect import save_manifest
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from graphify.export import to_json

# 1. Dummy semantic extraction
merged_sem = {'nodes': [], 'edges': [], 'hyperedges': [], 'input_tokens': 0, 'output_tokens': 0}
Path('graphify-out/.graphify_semantic.json').write_text(json.dumps(merged_sem, indent=2, ensure_ascii=False), encoding="utf-8")

# 2. Merge AST + Semantic
ast = json.loads(Path('graphify-out/.graphify_ast.json').read_text(encoding="utf-8"))
seen = {n['id'] for n in ast['nodes']}
merged_nodes = list(ast['nodes'])
merged_edges = ast['edges']
merged_hyperedges = []
merged = {
    'nodes': merged_nodes,
    'edges': merged_edges,
    'hyperedges': merged_hyperedges,
    'input_tokens': 0,
    'output_tokens': 0,
}
Path('graphify-out/.graphify_extract.json').write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")

# 3. Merge with existing graph.json
new_extraction = merged
incremental = json.loads(Path('graphify-out/.graphify_incremental.json').read_text(encoding="utf-8"))
deleted = list(incremental.get('deleted_files', []))

G_merged = build_merge([new_extraction], graph_path='graphify-out/graph.json', prune_sources=deleted or None)

merged_out = {
    'nodes': [{'id': n, **d} for n, d in G_merged.nodes(data=True)],
    'edges': [
        {**{k: val for k, val in d.items() if k not in ('_src', '_tgt', 'source', 'target')}, 'source': d.get('_src', u), 'target': d.get('_tgt', v)}
        for u, v, d in G_merged.edges(data=True)
    ],
    'hyperedges': list(G_merged.graph.get('hyperedges', [])),
    'input_tokens': 0,
    'output_tokens': 0,
}
Path('graphify-out/.graphify_extract.json').write_text(json.dumps(merged_out, ensure_ascii=False), encoding="utf-8")
save_manifest(incremental['files'])

# 4. Cluster, Analyze, Build Report
extraction = merged_out
detection = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding="utf-8"))

G = build_from_json(extraction)
communities = cluster(G)
cohesion = score_all(G, communities)
tokens = {'input': 0, 'output': 0}
gods = god_nodes(G)
surprises = surprising_connections(G, communities)
labels = {cid: 'Community ' + str(cid) for cid in communities}
questions = suggest_questions(G, communities, labels)

report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, '.', suggested_questions=questions)
Path('graphify-out/GRAPH_REPORT.md').write_text(report, encoding="utf-8")
to_json(G, communities, 'graphify-out/graph.json')

analysis = {
    'communities': {str(k): v for k, v in communities.items()},
    'cohesion': {str(k): v for k, v in cohesion.items()},
    'gods': gods,
    'surprises': surprises,
    'questions': questions,
}
Path('graphify-out/.graphify_analysis.json').write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
print(f'Graph updated: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, {len(communities)} communities')
