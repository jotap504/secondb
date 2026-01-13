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
            overflow-x: hidden;
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

        #chat-window {{
            transform: translateX(100%);
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        #chat-window.open {{
            transform: translateX(0);
        }}
        .spinner {{
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-left-color: #a855f7;
            border-radius: 50%;
            width: 16px;
            height: 16px;
            animation: spin 1s linear infinite;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
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
                <button onclick="toggleChat()" class="glass px-4 py-2 rounded-full text-sm font-medium border-purple-500/20 hover:bg-purple-500/10 transition-colors flex items-center gap-2">
                    <i data-lucide="message-square" class="w-4 h-4"></i>
                    IA Chat
                </button>
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
                                <td class="py-4 text-sm text-slate-400">{e.get("created_at")[:10] if e.get("created_at") else "N/A"}</td>
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

    <!-- Chat Overlay -->
    <div id="chat-window" class="fixed inset-y-0 right-0 w-full md:w-96 glass z-50 flex flex-col shadow-2xl border-l border-white/10">
        <div class="p-6 border-b border-white/10 flex justify-between items-center bg-white/5">
            <div class="flex items-center gap-3">
                <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                <h4 class="font-bold">IA Assistant</h4>
            </div>
            <button onclick="toggleChat()" class="p-2 hover:bg-white/10 rounded-full transition-colors">
                <i data-lucide="x" class="w-5 h-5"></i>
            </button>
        </div>
        
        <div id="chat-messages" class="flex-grow overflow-y-auto p-6 space-y-4">
            <div class="bg-blue-500/10 border border-blue-500/20 p-4 rounded-2xl text-sm">
                ¡Hola! Puedo ayudarte a registrar gastos, tareas o notas. Ej: "Gasté 500 en pizza"
            </div>
        </div>

        <!-- Attachment Preview -->
        <div id="attachment-preview" class="px-6 py-2 border-t border-white/10 bg-white/5 hidden">
            <div class="flex items-center justify-between p-2 bg-slate-900/80 rounded-xl border border-white/10">
                <div class="flex items-center gap-3 truncate">
                    <i id="preview-icon" data-lucide="image" class="w-4 h-4 text-purple-400"></i>
                    <span id="preview-name" class="text-xs text-slate-300 truncate font-medium">file.jpg</span>
                </div>
                <button onclick="clearAttachment()" class="p-1 hover:bg-white/10 rounded-full">
                    <i data-lucide="x" class="w-3 h-3 text-slate-500"></i>
                </button>
            </div>
        </div>

        <div class="p-6 border-t border-white/10 bg-white/5">
            <div class="flex items-end gap-2">
                <div class="flex-grow relative">
                    <input type="text" id="chat-input" 
                        class="w-full bg-slate-900/50 border border-white/10 rounded-2xl py-3 px-4 pr-12 focus:outline-none focus:border-purple-500/50 transition-all text-sm"
                        placeholder="Escribe un mensaje..."
                        onkeypress="if(event.key === 'Enter') sendMessage()">
                    
                    <div class="absolute right-2 top-1.5 flex gap-1">
                        <label for="image-upload" class="p-1.5 hover:bg-white/5 rounded-xl cursor-pointer text-slate-400 hover:text-purple-400 transition-colors">
                            <i data-lucide="image" class="w-4 h-4"></i>
                            <input type="file" id="image-upload" accept="image/*" class="hidden" onchange="handleFile(this, 'image')">
                        </label>
                        <label for="audio-upload" class="p-1.5 hover:bg-white/5 rounded-xl cursor-pointer text-slate-400 hover:text-blue-400 transition-colors">
                            <i data-lucide="mic" class="w-4 h-4"></i>
                            <input type="file" id="audio-upload" accept="audio/*" class="hidden" onchange="handleFile(this, 'audio')">
                        </label>
                    </div>
                </div>
                <button id="send-btn" onclick="sendMessage()" class="p-3 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl hover:scale-105 transition-transform shadow-lg shadow-purple-500/20 disabled:opacity-50 disabled:scale-100">
                    <i data-lucide="send" id="send-icon" class="w-5 h-5"></i>
                    <div id="send-spinner" class="spinner hidden"></div>
                </button>
            </div>
        </div>
    </div>

    <script>
        lucide.createIcons();

        let currentFile = null;
        let currentFileType = null;

        function toggleChat() {{
            const win = document.getElementById('chat-window');
            win.classList.toggle('open');
            if (win.classList.contains('open')) {{
                document.getElementById('chat-input').focus();
            }}
        }}

        function handleFile(input, type) {{
            const file = input.files[0];
            if (!file) return;

            currentFile = file;
            currentFileType = type;

            document.getElementById('preview-name').textContent = file.name;
            document.getElementById('preview-icon').setAttribute('data-lucide', type === 'image' ? 'image' : 'mic');
            document.getElementById('attachment-preview').classList.remove('hidden');
            lucide.createIcons();
            
            document.getElementById('chat-input').focus();
        }}

        function clearAttachment() {{
            currentFile = null;
            currentFileType = null;
            document.getElementById('image-upload').value = '';
            document.getElementById('audio-upload').value = '';
            document.getElementById('attachment-preview').classList.add('hidden');
        }}

        async function sendMessage() {{
            const input = document.getElementById('chat-input');
            const msg = input.value.trim();
            const btn = document.getElementById('send-btn');
            const icon = document.getElementById('send-icon');
            const spinner = document.getElementById('send-spinner');

            if (!msg && !currentFile) return;

            btn.disabled = true;
            icon.classList.add('hidden');
            spinner.classList.remove('hidden');

            addMessage(msg || (currentFileType === 'image' ? '🖼️ Imagen enviada' : '🎙️ Audio enviado'), 'user');
            input.value = '';

            const formData = new FormData();
            formData.append('message', msg || "Analiza este archivo");
            if (currentFile) {{
                formData.append(currentFileType, currentFile);
            }}

            clearAttachment();

            try {{
                const response = await fetch('/api/chat', {{
                    method: 'POST',
                    body: formData
                }});
                
                const data = await response.json();
                addMessage(data.response, 'bot');
                
                if (data.category && data.category !== 'OTHER') {{
                    setTimeout(() => location.reload(), 2500);
                }}
            }} catch (e) {{
                addMessage('Error: No pude conectar con el servidor.', 'bot');
            }} finally {{
                btn.disabled = false;
                icon.classList.remove('hidden');
                spinner.classList.add('hidden');
            }}
        }}

        function addMessage(text, side) {{
            const container = document.getElementById('chat-messages');
            const div = document.createElement('div');
            div.className = side === 'user' 
                ? 'bg-white/10 ml-8 p-4 rounded-2xl text-sm' 
                : 'bg-gradient-to-br from-blue-600/20 to-purple-600/20 border border-white/5 mr-8 p-4 rounded-2xl text-sm shadow-xl';
            div.textContent = text;
            container.appendChild(div);
            container.scrollTop = container.scrollHeight;
        }}

        Chart.defaults.color = '#94a3b8';
        Chart.defaults.font.family = 'Plus Jakarta Sans';

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
