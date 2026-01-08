import os
import json
import asyncio
from database import supabase
from datetime import datetime

async def fetch_supabase_data_async():
    """Fetch necessary data from Supabase asynchronously."""
    try:
        # Using asyncio.to_thread because the current supabase-py client is synchronous
        expenses_task = asyncio.to_thread(
            lambda: supabase.table("expenses").select("*").order("created_at", desc=True).limit(200).execute().data
        )
        tasks_task = asyncio.to_thread(
            lambda: supabase.table("tasks").select("*").order("created_at", desc=True).execute().data
        )
        notes_task = asyncio.to_thread(
            lambda: supabase.table("notes").select("*").order("created_at", desc=True).limit(50).execute().data
        )
        
        expenses, tasks, notes = await asyncio.gather(expenses_task, tasks_task, notes_task)
        return expenses, tasks, notes
    except Exception as e:
        print(f"Error fetching data: {e}")
        return [], [], []

def generate_html(expenses, tasks, notes):
    """Generate the premium HTML content with Chart.js and refined aesthetics."""
    
    total_expenses = sum(float(e.get('amount', 0)) for e in expenses)
    pending_tasks = len([t for t in tasks if t.get('status') == 'pending'])
    total_notes = len(notes)
    
    # Process Category Data for Pie Chart
    cat_data = {}
    for e in expenses:
        # If the direct description doesn't look like a category, we'd need better data, 
        # but for now we'll use description as a proxy or "General"
        desc = e.get('description', 'Otros')
        cat_data[desc] = cat_data.get(desc, 0) + float(e.get('amount', 0))
    
    # Limit to top 5 categories
    sorted_cats = sorted(cat_data.items(), key=lambda x: x[1], reverse=True)[:5]
    cat_labels = [c[0] for c in sorted_cats]
    cat_values = [c[1] for c in sorted_cats]

    # Process Daily Data for Line Chart
    daily_data = {}
    for e in expenses:
        date_str = e.get('created_at', '')[:10]
        if date_str:
            daily_data[date_str] = daily_data.get(date_str, 0) + float(e.get('amount', 0))
    
    sorted_dates = sorted(daily_data.keys())[-7:] # Last 7 days
    daily_values = [daily_data[d] for d in sorted_dates]

    template = f"""
<!DOCTYPE html>
<html lang="es" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Life OS - Premium Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
        body {{ 
            font-family: 'Plus Jakarta Sans', sans-serif; 
            background: radial-gradient(circle at top right, #1e293b, #0f172a, #020617);
        }}
        .glass {{ 
            background: rgba(15, 23, 42, 0.6); 
            backdrop-filter: blur(16px); 
            border: 1px solid rgba(255, 255, 255, 0.08); 
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }}
        .card-hover:hover {{
            transform: translateY(-4px);
            border-color: rgba(255, 255, 255, 0.2);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .text-gradient {{
            background: linear-gradient(to right, #60a5fa, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        ::-webkit-scrollbar {{ width: 6px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: #334155; border-radius: 10px; }}
    </style>
</head>
<body class="text-slate-200 min-h-screen Selection:bg-purple-500/30">
    <div class="max-w-7xl mx-auto p-4 md:p-8 space-y-8">
        <!-- Header -->
        <header class="flex justify-between items-center mb-12">
            <div>
                <h1 class="text-4xl font-extrabold tracking-tight text-gradient">AI Life OS</h1>
                <p class="text-slate-400 mt-2 flex items-center gap-2">
                    <i data-lucide="calendar" class="w-4 h-4"></i>
                    Actualizado hoy a las {datetime.now().strftime('%H:%M')}
                </p>
            </div>
            <div class="flex gap-4">
                <div class="glass px-4 py-2 rounded-full text-sm font-medium border-purple-500/20">
                    Sincronizado con Supabase
                </div>
            </div>
        </header>

        <!-- Stats Grid -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="glass p-6 rounded-3xl card-hover relative overflow-hidden group">
                <div class="absolute -right-4 -top-4 w-24 h-24 bg-blue-500/10 rounded-full blur-2xl group-hover:bg-blue-500/20 transition-all"></div>
                <div class="flex items-center gap-4 mb-4">
                    <div class="p-3 bg-blue-500/10 rounded-2xl text-blue-400">
                        <i data-lucide="wallet"></i>
                    </div>
                    <p class="text-sm font-semibold text-slate-400 uppercase tracking-wider">Total Gastado</p>
                </div>
                <h3 class="text-3xl font-bold">${total_expenses:,.2f}</h3>
            </div>

            <div class="glass p-6 rounded-3xl card-hover relative overflow-hidden group">
                <div class="absolute -right-4 -top-4 w-24 h-24 bg-purple-500/10 rounded-full blur-2xl group-hover:bg-purple-500/20 transition-all"></div>
                <div class="flex items-center gap-4 mb-4">
                    <div class="p-3 bg-purple-500/10 rounded-2xl text-purple-400">
                        <i data-lucide="check-circle-2"></i>
                    </div>
                    <p class="text-sm font-semibold text-slate-400 uppercase tracking-wider">Tareas Pendientes</p>
                </div>
                <h3 class="text-3xl font-bold">{pending_tasks}</h3>
            </div>

            <div class="glass p-6 rounded-3xl card-hover relative overflow-hidden group">
                <div class="absolute -right-4 -top-4 w-24 h-24 bg-indigo-500/10 rounded-full blur-2xl group-hover:bg-indigo-500/20 transition-all"></div>
                <div class="flex items-center gap-4 mb-4">
                    <div class="p-3 bg-indigo-500/10 rounded-2xl text-indigo-400">
                        <i data-lucide="sticky-note"></i>
                    </div>
                    <p class="text-sm font-semibold text-slate-400 uppercase tracking-wider">Notas Guardadas</p>
                </div>
                <h3 class="text-3xl font-bold">{total_notes}</h3>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="glass p-8 rounded-3xl">
                <h4 class="text-xl font-bold mb-8 flex items-center gap-3">
                    <i data-lucide="bar-chart-3" class="text-blue-400"></i>
                    Gastos por Categoría
                </h4>
                <div class="h-64">
                    <canvas id="categoryChart"></canvas>
                </div>
            </div>
            <div class="glass p-8 rounded-3xl">
                <h4 class="text-xl font-bold mb-8 flex items-center gap-3">
                    <i data-lucide="trending-up" class="text-purple-400"></i>
                    Tendencia de Gastos (7 días)
                </h4>
                <div class="h-64">
                    <canvas id="trendChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Recent Items -->
        <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
            <!-- Recent Expenses Table -->
            <div class="xl:col-span-2 glass p-8 rounded-3xl">
                <div class="flex justify-between items-center mb-8">
                    <h4 class="text-xl font-bold flex items-center gap-3">
                        <i data-lucide="list" class="text-slate-400"></i>
                        Movimientos Recientes
                    </h4>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left">
                        <thead>
                            <tr class="text-slate-500 text-xs uppercase tracking-widest border-b border-slate-700/50">
                                <th class="pb-4 font-semibold">Fecha</th>
                                <th class="pb-4 font-semibold">Concepto</th>
                                <th class="pb-4 font-semibold text-right">Monto</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800/50">
                            {''.join([f'''
                            <tr class="group hover:bg-slate-800/30 transition-colors">
                                <td class="py-4 text-sm text-slate-400">{e.get("created_at")[:10]}</td>
                                <td class="py-4 font-medium">{e.get("description")}</td>
                                <td class="py-4 text-right font-bold text-blue-400">${float(e.get("amount", 0)):,.2f}</td>
                            </tr>''' for e in expenses[:10]])}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Urgent Tasks -->
            <div class="glass p-8 rounded-3xl">
                <h4 class="text-xl font-bold mb-8 flex items-center gap-3">
                    <i data-lucide="clock" class="text-orange-400"></i>
                    Tareas Pendientes
                </h4>
                <div class="space-y-4">
                    {''.join([f'''
                    <div class="flex items-center gap-4 p-4 rounded-2xl bg-slate-800/30 border border-slate-700/30">
                        <div class="w-2 h-2 rounded-full bg-orange-400 shadow-[0_0_8px_rgba(251,146,60,0.5)]"></div>
                        <p class="text-sm font-medium flex-grow truncate">{t.get("description")}</p>
                    </div>''' for t in [t for t in tasks if t.get('status') == 'pending'][:5]]) or '<p class="text-slate-500 text-center py-8">No hay tareas pendientes</p>'}
                </div>
            </div>
        </div>
    </div>

    <script>
        lucide.createIcons();

        // Common Chart Config
        Chart.defaults.color = '#94a3b8';
        Chart.defaults.font.family = 'Plus Jakarta Sans';

        // Category Chart
        const catCtx = document.getElementById('categoryChart').getContext('2d');
        new Chart(catCtx, {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(cat_labels)},
                datasets: [{{
                    data: {json.dumps(cat_values)},
                    backgroundColor: ['#3b82f6', '#a855f7', '#6366f1', '#10b981', '#f59e0b'],
                    borderWidth: 0,
                    spacing: 8
                }}]
            }},
            options: {{
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'bottom', labels: {{ padding: 20, usePointStyle: true }} }}
                }},
                cutout: '70%'
            }}
        }});

        // Trend Chart
        const trendCtx = document.getElementById('trendChart').getContext('2d');
        new Chart(trendCtx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(sorted_dates)},
                datasets: [{{
                    label: 'Gastos Diarios',
                    data: {json.dumps(daily_values)},
                    borderColor: '#a855f7',
                    backgroundGradient: 'linear-gradient(180deg, rgba(168, 85, 247, 0.2) 0%, rgba(168, 85, 247, 0) 100%)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: '#a855f7'
                }}]
            }},
            options: {{
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, border: {{ display: false }} }},
                    x: {{ grid: {{ display: false }}, border: {{ display: false }} }}
                }}
            }}
        }});
    </script>
</body>
</html>
    """
    return template

async def generate_dashboard_file_async():
    """Main function to generate the dashboard HTML file asynchronously."""
    try:
        print("Fetching data from Supabase (Async)...")
        exp, tsk, nts = await fetch_supabase_data_async()
        print(f"Found {len(exp)} expenses, {len(tsk)} tasks, and {len(nts)} notes.")
        
        html_content = generate_html(exp, tsk, nts)
        
        file_path = "dashboard.html"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"Dashboard generated successfully: {os.path.abspath(file_path)}")
        return True
    except Exception as e:
        print(f"Error generating dashboard: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(generate_dashboard_file_async())
