import matplotlib.pyplot as plt
import ast
import os

def parse_log(filepath):
    loss_data = []
    eval_loss_data = []
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = ast.literal_eval(line)
                if 'epoch' in data:
                    epoch = data['epoch']
                    if 'loss' in data:
                        loss_data.append((epoch, data['loss']))
                    if 'eval_loss' in data:
                        eval_loss_data.append((epoch, data['eval_loss']))
            except (ValueError, SyntaxError):
                continue
                
    return loss_data, eval_loss_data

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    log2_path = os.path.join(current_dir, 'log2.log')
    
    log2_loss, log2_eval = parse_log(log2_path)
    
    # Plotting
    plt.figure(figsize=(10, 6))
    
    if log2_loss:
        x_loss, y_loss = zip(*log2_loss)
        plt.plot(x_loss, y_loss, label='Training Loss', marker='.', linestyle='-', alpha=0.5, color='blue')
        
    if log2_eval:
        x_eval, y_eval = zip(*log2_eval)
        plt.plot(x_eval, y_eval, label='Evaluation Loss', marker='o', linestyle='-', color='red')

    plt.title('Log2 Training and Evaluation Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.yscale('log')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    output_path = os.path.join(current_dir, 'log2_full_training.png')
    plt.savefig(output_path)
    print(f"Graph saved to {output_path}")

if __name__ == "__main__":
    main()
