import json
import os
from collections import defaultdict

def analyze_results():
    file_path = "evaluation_results.json"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Organize data by query
    # structure: { query_text: { index_name: relevant_count } }
    query_map = defaultdict(dict)
    
    method_names = []
    
    for method_data in data:
        index_name = method_data['index_name']
        method_names.append(index_name)
        for detail in method_data['details']:
            q = detail['query']
            count = detail['relevant_count']
            query_map[q][index_name] = count

    # Initialize scores
    scores = {name: 0.0 for name in method_names}
    win_counts = {name: 0 for name in method_names}
    total_relevant = {name: 0 for name in method_names}
    
    # Weights
    # 1st: 3 pts, 2nd: 2 pts, 3rd: 1 pt
    
    print(f"Analyzing {len(query_map)} queries...")
    
    for query, counts in query_map.items():
        # counts: {'Original': 17, 'Chunk 200': 10, ...}
        
        # Sort by count descending
        sorted_methods = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        
        # Calculate ranks handling ties
        # We assign points based on rank positions available (3, 2, 1)
        # If there is a tie, we average the points for those positions.
        
        current_rank_idx = 0
        while current_rank_idx < len(sorted_methods):
            # Find ties
            current_score = sorted_methods[current_rank_idx][1]
            tie_group = [sorted_methods[current_rank_idx]]
            
            next_idx = current_rank_idx + 1
            while next_idx < len(sorted_methods) and sorted_methods[next_idx][1] == current_score:
                tie_group.append(sorted_methods[next_idx])
                next_idx += 1
            
            # Calculate points for this group
            # Positions involved: current_rank_idx, current_rank_idx+1, ...
            # Points available: 3, 2, 1 corresponding to indices 0, 1, 2
            
            points_sum = 0
            for i in range(len(tie_group)):
                rank_pos = current_rank_idx + i
                if rank_pos == 0: points_sum += 3
                elif rank_pos == 1: points_sum += 2
                elif rank_pos == 2: points_sum += 1
            
            avg_points = points_sum / len(tie_group)
            
            for method_name, count in tie_group:
                scores[method_name] += avg_points
                total_relevant[method_name] += count
                
                # Count wins (strict or shared)
                if current_rank_idx == 0:
                    win_counts[method_name] += 1
            
            current_rank_idx = next_idx

    # Prepare Output
    output_lines = []
    output_lines.append("\n" + "="*60)
    output_lines.append("🏆 Indexing Method Comparison Results")
    output_lines.append("="*60)
    
    # Sort by Score
    sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    output_lines.append(f"{'Rank':<5} {'Method Name':<25} {'Score':<10} {'Avg Rel':<10} {'Wins':<5}")
    output_lines.append("-" * 60)
    
    for i, (name, score) in enumerate(sorted_results, 1):
        avg_rel = total_relevant[name] / len(query_map)
        wins = win_counts[name]
        output_lines.append(f"{i:<5} {name:<25} {score:<10.1f} {avg_rel:<10.2f} {wins:<5}")
        
    output_lines.append("-" * 60)
    output_lines.append("* Score Calculation: 1st=3pts, 2nd=2pts, 3rd=1pt (Ties split points)")
    output_lines.append("* Avg Rel: Average number of relevant documents retrieved in Top 20")
    output_lines.append("* Wins: Number of queries where the method was 1st (including ties)")
    output_lines.append("="*60)

    # Print to console
    print("\n".join(output_lines))

    # Save to file
    with open("analysis_summary.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print("\nResults saved to analysis_summary.txt")

if __name__ == "__main__":
    analyze_results()
