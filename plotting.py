import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64
from io import BytesIO

def generate_income_plot(days, income, period):
    try:
        fig, ax = plt.subplots(figsize=(10, 5))
        
        if days:
            bars = ax.bar(days, income, color='#ff9800', edgecolor='#e68900', linewidth=1.2)
            
            for bar, val in zip(bars, income):
                height = bar.get_height()
                ax.annotate(f'{val:.0f}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=9, color='#333')
        else:
            ax.text(0.5, 0.5, 'Немає даних за обраний період', ha='center', va='center', fontsize=14)
            
        ax.set_title(f'Статистика ({period})', fontsize=14, fontweight='bold')
        ax.set_xlabel('Час', fontsize=11)
        ax.set_ylabel('Значення', fontsize=11)
        ax.tick_params(axis='x', rotation=45)
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plot_url = base64.b64encode(buf.getvalue()).decode('utf8')
        plt.close(fig)
        return plot_url
    except Exception as e:
        print(f"Помилка побудови графіка: {e}")
        return None

def generate_maintenance_plot(dates, costs, car_name):
    try:
        fig, ax = plt.subplots(figsize=(10, 5))
        
        if dates and costs:
            ax.plot(dates, costs, marker='o', linestyle='-', color='#2196F3', 
                    linewidth=2, markersize=8, markerfacecolor='#1976D2', markeredgecolor='white')
            
            ax.fill_between(dates, costs, alpha=0.2, color='#2196F3')
            
            for i, (x, y) in enumerate(zip(dates, costs)):
                ax.annotate(f'{y:.0f} грн',
                            xy=(x, y),
                            xytext=(0, 10),
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=9, 
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='#2196F3', alpha=0.8))
            
            total = sum(costs)
            ax.axhline(y=sum(costs)/len(costs), color='#f44336', linestyle='--', 
                       alpha=0.7, label=f'Середнє: {total/len(costs):.0f} грн')
            ax.legend(loc='upper right')
        else:
            ax.text(0.5, 0.5, 'Немає записів про обслуговування', ha='center', va='center', fontsize=14)
            
        ax.set_title(f'Витрати на обслуговування: {car_name}', fontsize=14, fontweight='bold')
        ax.set_xlabel('Дата', fontsize=11)
        ax.set_ylabel('Вартість (грн)', fontsize=11)
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plot_url = base64.b64encode(buf.getvalue()).decode('utf8')
        plt.close(fig)
        return plot_url
    except Exception as e:
        print(f"Помилка побудови графіка обслуговування: {e}")
        return None

def generate_maintenance_summary_plot(car_names, total_costs):
    try:
        fig, ax = plt.subplots(figsize=(10, max(5, len(car_names) * 0.5)))
        
        if car_names and total_costs:
            colors = plt.cm.Blues([0.4 + 0.4 * i / len(car_names) for i in range(len(car_names))])
            bars = ax.barh(car_names, total_costs, color=colors, edgecolor='#1565C0')
            
            for bar, val in zip(bars, total_costs):
                ax.annotate(f'{val:.0f} грн',
                            xy=(val, bar.get_y() + bar.get_height() / 2),
                            xytext=(5, 0),
                            textcoords="offset points",
                            ha='left', va='center', fontsize=10, fontweight='bold')
        else:
            ax.text(0.5, 0.5, 'Немає даних про обслуговування', ha='center', va='center', fontsize=14)
            
        ax.set_title('Загальні витрати на обслуговування по авто', fontsize=14, fontweight='bold')
        ax.set_xlabel('Загальна вартість (грн)', fontsize=11)
        ax.grid(axis='x', alpha=0.3)
        
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plot_url = base64.b64encode(buf.getvalue()).decode('utf8')
        plt.close(fig)
        return plot_url
    except Exception as e:
        print(f"Помилка побудови зведеного графіка: {e}")
        return None
