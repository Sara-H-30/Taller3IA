"""Ventana Tk. Red/CPT, estimaciones y barridos del MDP."""
import tkinter as tk
from tkinter import ttk
import math

BG, INK, GREEN = '#e8eef5', '#17365d', '#2e9d62'
BLUE, MUTED = '#2563b8', '#617184'
ARROWS = {'N': '↑', 'E': '→', 'S': '↓', 'W': '←', None: ''}
TITLES = {1: 'Probabilidades y utilidad esperada', 2: 'Inferencia por enumeración',
          3: 'Eliminación y muestreo', 4: 'Iteración de valores', 5: 'Política del dron'}


def number(value):
    return 'Sin estimación' if value is None else f'{value:.6f}'


def table(parent, columns, rows=(), widths=None):
    """Tabla desplazable; separa etiquetas y números sin exponer serialización."""
    holder = ttk.Frame(parent)
    holder.pack(fill='both', expand=True, padx=10, pady=10)
    holder.columnconfigure(0, weight=1)
    holder.rowconfigure(0, weight=1)
    tree = ttk.Treeview(holder, columns=list(range(len(columns))), show='headings', height=8)
    for i, name in enumerate(columns):
        tree.heading(i, text=name)
        tree.column(i, width=widths[i] if widths else 145, minwidth=85, anchor='center')
    vs = ttk.Scrollbar(holder, orient='vertical', command=tree.yview)
    hs = ttk.Scrollbar(holder, orient='horizontal', command=tree.xview)
    tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
    tree.grid(row=0, column=0, sticky='nsew')
    vs.grid(row=0, column=1, sticky='ns')
    hs.grid(row=1, column=0, sticky='ew')
    tree.tag_configure('even', background='#f0f5fa')
    tree.tag_configure('selected', background='#fff0cc')
    tree.tag_configure('best', background='#daf0e1')
    for i, row in enumerate(rows):
        tree.insert('', 'end', values=row, tags=('even',) if i % 2 == 0 else ())
    return tree


class Viewer:
    def __init__(self, root, report, model, frame_time=0.3):
        self.root, self.report, self.model = root, report, model
        self.frame_time = max(30, int(frame_time * 1000))
        self.playing = False
        self.timer = None
        root.title(f'Alerta Bosque | Punto {report["point"]} | {model.name}')
        root.geometry('1120x780')
        root.minsize(1120, 780)
        root.configure(bg=BG)
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('TFrame', background=BG)
        style.configure('TLabel', background=BG, foreground=INK, font=('Segoe UI', 10))
        style.configure('TButton', font=('Segoe UI', 10), padding=6)
        style.configure('TNotebook', background=BG, borderwidth=0)
        style.configure('TNotebook.Tab', padding=(10, 7), font=('Segoe UI', 9),background='#e8eef5')
        style.map('TNotebook.Tab', background=[('selected', '#ffffff')], foreground=[('selected', BLUE)])
        style.configure('Treeview', font=('Segoe UI', 10), rowheight=30, background='white', fieldbackground='white')
        style.configure('Treeview.Heading', background=INK, foreground='white', font=('Segoe UI', 10, 'bold'))
        style.map('Treeview', background=[('selected', '#c9e1f8')], foreground=[('selected', INK)])
        panel = tk.Frame(root, bg='#f8fafc', width=350)
        panel.pack(side='right', fill='y')
        panel.pack_propagate(False)
        tk.Label(panel, text='ALERTA BOSQUE', bg=INK, fg='white',
                 font=('Segoe UI', 17, 'bold'), anchor='w', padx=20, pady=15).pack(fill='x')
        execution = tk.Frame(panel, bg='white', highlightbackground='#d8e0e8', highlightthickness=1)
        execution.pack(fill='x', padx=12, pady=(10,8))
        for text, size, weight, color in [('EJECUCIÓN',9,'bold',INK),
                (f'Punto {report["point"]} · {TITLES[report["point"]]}',12,'bold',INK),
                (model.name,9,'bold',BLUE), (model.description,9,'normal',MUTED)]:
            tk.Label(execution,text=text,bg='white',fg=color,font=('Segoe UI',size,weight),
                     anchor='w',justify='left',wraplength=300).pack(fill='x',padx=12,pady=5)
        self.info_canvas = tk.Canvas(panel,bg='#f8fafc',highlightthickness=0)
        self.info_canvas.pack(fill='both',expand=True)
        workspace = tk.Frame(root,bg=BG)
        workspace.pack(side='left',fill='both',expand=True)
        self.notebook = ttk.Notebook(workspace)
        frame = ttk.Frame(self.notebook)
        sampling = report['point'] == 3 and report['method'] in ('prior', 'rejection')
        title = ('Red' if report['point'] <= 3 else
                 'Política' if report['point'] == 5 else 'Valores')
        self.notebook.add(frame, text=title)
        self.canvas = tk.Canvas(frame, bg=BG, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.build_tables()
        if report['point'] == 1:
            self.prioritize_tabs(['Conjunta', 'Probabilidades', 'Decisiones'])
        elif sampling:
            self.prioritize_tabs(['Ejecuciones', 'Probabilidades'])
        elif report.get('method') == 'elimination':
            self.prioritize_tabs(['Factores', 'Probabilidades'])
        controls = tk.Frame(workspace,bg='white',highlightbackground='#d4dde7',highlightthickness=1)
        self.playback_buttons = []
        def button(label, command):
            widget = tk.Button(controls,text=label,command=command,relief='flat',bd=0,
                             bg='white',fg='#244a72',activebackground='#dbeafe',
                             cursor='hand2',width=4,font=('Segoe UI Symbol',14,'bold'))
            self.playback_buttons.append(widget)
            return widget
        button('↺',self.restart).pack(side='left',padx=(5,1),pady=4)
        button('⏮',lambda: self.manual_step(-1)).pack(side='left',padx=1)
        self.play_button = button('▶',self.toggle)
        self.play_button.pack(side='left')
        button('⏭',lambda: self.manual_step(1)).pack(side='left',padx=1)
        self.mode = tk.StringVar(value='Política' if report['point'] == 5 else 'Valores')
        if report['point'] == 5:
            selector = ttk.Combobox(controls, textvariable=self.mode, values=['Política', 'Trayectoria'], state='readonly', width=13)
            selector.pack(side='left', padx=8)
            selector.bind('<<ComboboxSelected>>', lambda e: self.reset_mode())
        self.index = tk.IntVar(value=self.last_frame() if sampling or report['point'] == 5 else 0)
        self.slider = tk.Scale(controls, from_=0, to=self.last_frame(), orient='horizontal', variable=self.index,
                               showvalue=False, command=lambda v: self.draw(), highlightthickness=0,
                               bg='white',troughcolor=BG,bd=0,sliderrelief='flat')
        self.slider.pack(side='left', fill='x', expand=True, padx=8)
        self.status = ttk.Label(workspace, text='', padding=10,wraplength=720,font=('Segoe UI',9))
        # Reserve the footer before allocating the expanding notebook.
        self.notebook.pack_forget()
        controls.pack_forget()
        self.status.pack(side='bottom', fill='x')
        if self.last_frame() > 0 or report['point'] == 5:
            controls.pack(side='bottom', fill='x', padx=14, pady=8)
        self.notebook.pack(fill='both', expand=True, padx=12,pady=(12,0))
        self.canvas.bind('<Configure>', lambda e: self.draw())
        self.info_canvas.bind('<Configure>', lambda e: self.draw())
        self.canvas.bind('<Button-1>', self.inspect_node)
        root.bind('<space>', lambda e: self.toggle())
        root.bind('<Right>', lambda e: self.manual_step(1))
        root.bind('<Left>', lambda e: self.manual_step(-1))
        root.bind('r', lambda e: self.restart())
        root.bind('R', lambda e: self.restart())
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.draw()

    def tab(self, title, explanation):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=title)
        ttk.Label(frame, text=explanation, wraplength=680, padding=10).pack(fill='x')
        return frame

    def prioritize_tabs(self, titles):
        for position, title in enumerate(titles):
            for tab in self.notebook.tabs():
                if self.notebook.tab(tab, 'text') == title:
                    self.notebook.insert(position, tab)
                    break
        self.notebook.select(0)

    def build_tables(self):
        r, m = self.report, self.model
        if r['point'] <= 3:
            from models.bayes import basic_distribution
            evidence = r['evidence']
            if r['point'] == 2:
                tab = self.tab('Probabilidades', 'Distribución obtenida por enumeración. Use el cálculo del punto 1 como control en sensor_basico.')
                table(tab, ['Resultado', 'Probabilidad obtenida'],
                      [(f'{r["query"]}={v}', number(r['distribution'][v])) for v in (0,1)])
            elif r['point'] == 3:
                tab = self.tab('Probabilidades', 'Resultado del método y referencia por enumeración del punto 2.')
                table(tab, ['Resultado', 'Probabilidad obtenida', 'Referencia exacta'],
                      [(f'{r["query"]}={v}', number(r['distribution'][v] if r['distribution'] else None),
                        number(r['exact'][v])) for v in (0, 1)])
            else:
                weights = basic_distribution(m, r['query'], evidence)
                total = sum(weights.values())
                columns = ['Resultado', 'P(resultado, evidencia)', 'P(evidencia)']
                columns.append('Resultado del método')
                rows = [(f'{r["query"]}={v}', number(weights[v]), number(total),
                         number(r['distribution'][v]) if r['distribution'] else 'Sin estimación') for v in (0, 1)]
                tab = self.tab('Probabilidades', 'Filtrar por evidencia → sumar mundos compatibles → normalizar.')
                table(tab, columns, rows)
            if r['point'] == 1:
                tab = self.tab('Conjunta', 'Cada fila es un mundo posible. En amarillo: filas compatibles con la evidencia seleccionada.')
                tree = table(tab, [*m.variables, 'Probabilidad', 'Compatible'])
                for row in r['joint_table']:
                    match = all(row['event'][x] == v for x, v in evidence.items())
                    tree.insert('', 'end', values=[*[row['event'][x] for x in m.variables], number(row['probability']), 'Sí' if match else 'No'],
                                tags=('selected',) if match else ())
            if r.get('utilities'):
                tab = self.tab('Decisiones', 'EU(a)=P(0)·U(a,0)+P(1)·U(a,1). Verde: acción de mayor utilidad esperada con la distribución calculada.')
                tree = table(tab, ['Acción', 'U(a,0)', 'U(a,1)', 'P(0)·U(a,0)', 'P(1)·U(a,1)', 'EU(a)'],
                             widths=[120,85,85,125,125,100])
                for a, value in r['utilities'].items():
                    u = m.utilities[a]
                    tree.insert('', 'end', values=(a, u['0'], u['1'], number(r['distribution'][0]*u['0']),
                                number(r['distribution'][1]*u['1']), number(value)), tags=('best',) if a == r['action'] else ())
            if r['method'] == 'elimination':
                peak = max((step['product_rows'] for step in r['history']), default=1)
                tab = self.tab('Factores', f'Mayor factor intermedio (producto): {peak} filas. Recorra los pasos con los controles inferiores para ver el factor después de sumar la variable eliminada.')
                self.factor_label = ttk.Label(tab, text='', padding=10)
                self.factor_label.pack(fill='x')
                self.factor_tree = table(tab, ['Asignación de las variables restantes', 'Factor resultante'], widths=[450,180])
            if r['point'] == 3 and r['method'] in ('prior', 'rejection'):
                tab = self.tab('Ejecuciones', 'Muestras aceptadas y error absoluto frente al valor exacto.')
                rows = [(i+1, row['seed'], row['generated'], row['accepted'],
                         f'{row["accepted"]/row["generated"]:.1%}',
                         number(row['p1']), number(row['absolute_error']))
                        for i, row in enumerate(r['repetitions'])]
                table(tab, ['Ejecución', 'Semilla', 'Intentos', 'Aceptadas', 'Aceptación', 'P(consulta=1)', 'Error absoluto'], rows,
                      widths=[85,85,85,85,90,125,125])
            tab = self.tab('Tablas locales', 'CPT de la red. Las condiciones se muestran con nombres de variables, no como claves binarias.')
            rows = []
            for node in m.nodes:
                for bits, p in node['cpt'].items():
                    condition = ', '.join(f'{x}={v}' for x, v in zip(node['parents'], bits)) or 'Sin padres'
                    rows.append((node['name'], condition, number(1-p), number(p)))
            table(tab, ['Variable', 'Condición sobre padres', 'P(variable=0)', 'P(variable=1)'], rows, [170,440,160,160])
        else:
            tab = self.tab('Convergencia', 'Cada fila representa un barrido sincrónico. El límite de iteraciones no garantiza convergencia.')
            table(tab, ['Barrido', 'Cambio máximo', 'V(inicio)', 'Cumple tolerancia'],
                  [(i+1, f'{d:.9g}', number(r['history'][i+1][f'{m.start[0]},{m.start[1]}']),
                    'Sí' if d < r.get('tolerance', 1e-8) else 'No') for i,d in enumerate(r['deltas'])])
            tab = self.tab('Estados y acciones', 'Valores finales. Para inspeccionar un barrido, seleccione una celda en la visualización: se abre el cálculo de Bellman.')
            from algorithms.planning import action_value
            values = {s:r['values'][f'{s[0]},{s[1]}'] for s in m.states}
            rows = []
            for s in m.states:
                key = f'{s[0]},{s[1]}'
                rows.append((key, number(values[s]), *[number(action_value(m,s,a,values)) if m.actions(s) else 'Terminal' for a in ('N','E','S','W')],
                             (r['policy'] or {}).get(key) or ('Terminal' if not m.actions(s) else 'Punto 5')))
            table(tab, ['Estado (x,y)', 'V final', 'Q(N)', 'Q(E)', 'Q(S)', 'Q(W)', 'Política'], rows)

    def card(self, x, y, width, title, lines):
        """Tarjetas en el panel lateral, con la paleta de Red Centinela."""
        c = self.info_canvas
        height = 45 + 23*len(lines)
        c.create_rectangle(x,y,x+width,y+height,fill='white',outline='#d8e0e8')
        c.create_text(x+12,y+12,text=title,anchor='nw',font=('Segoe UI',9,'bold'),fill=INK,width=width-24)
        for i, line in enumerate(lines):
            c.create_text(x+12,y+39+i*23,text=line,anchor='nw',font=('Segoe UI',9),fill=INK,width=width-24)
        return y+height+10

    def last_frame(self):
        if self.report['point'] == 5:
            return len(self.report['trajectory']['path'])-1 if self.mode.get() == 'Trayectoria' else 0
        return max(0, len(self.report['history'])-1)

    def reset_mode(self):
        self.playing = False
        self.play_button.configure(text='▶')
        self.slider.configure(to=self.last_frame())
        self.index.set(0)
        self.draw()

    def restart(self):
        self.playing = False
        self.play_button.configure(text='▶')
        self.index.set(0)
        self.draw()

    def step(self, delta):
        self.index.set(max(0, min(self.last_frame(), self.index.get()+delta)))
        self.draw()

    def manual_step(self, delta):
        self.playing = False
        self.play_button.configure(text='▶')
        self.step(delta)

    def toggle(self):
        if self.last_frame() == 0:
            return
        self.playing = not self.playing
        self.play_button.configure(text='⏸' if self.playing else '▶')
        if self.playing:
            if self.index.get() >= self.last_frame():
                self.index.set(0)
            self.tick()

    def tick(self):
        if self.timer:
            self.root.after_cancel(self.timer)
            self.timer = None
        if not self.playing:
            return
        self.step(1)
        if self.index.get() < self.last_frame():
            self.timer = self.root.after(self.frame_time, self.tick)
        else:
            self.playing = False
            self.play_button.configure(text='▶')

    def close(self):
        if self.timer:
            self.root.after_cancel(self.timer)
        self.root.destroy()

    def draw(self):
        c = self.canvas
        c.delete('all')
        self.info_canvas.delete('all')
        width, height = max(c.winfo_width(), 700), max(c.winfo_height(), 350)
        if self.report['point'] <= 3:
            self.draw_bayes(width, height)
        else:
            self.draw_mdp(width, height)

    def draw_network(self, width, height):
        c, r = self.canvas, self.report
        left = width
        c.create_text(20,16,text='RED BAYESIANA',anchor='nw',font=('Segoe UI',10,'bold'),fill=INK)
        c.create_text(20,height-16,text='Amarillo: evidencia   ·   Azul: consulta   ·   Pulse un nodo para ver su CPT',anchor='w',font=('Segoe UI',9),fill=MUTED)
        positions = {n['name']: (40+n['position'][0]*(left-80), 40+n['position'][1]*(height-105)) for n in self.model.nodes}
        for node in self.model.nodes:
            x, y = positions[node['name']]
            for parent in node['parents']:
                px, py = positions[parent]
                dx, dy = x-px, y-py
                fraction = 1 / math.sqrt((dx/56)**2 + (dy/24)**2)
                c.create_line(px+dx*fraction, py+dy*fraction,
                              x-dx*fraction, y-dy*fraction,
                              arrow='last', arrowshape=(10, 12, 5), width=2, fill='#687d6d')
        self.node_positions = positions
        for name, (x, y) in positions.items():
            observed = name in r['evidence']
            c.create_oval(x-56, y-24, x+56, y+24, fill='#f2b134' if observed else '#d4e5fa' if name == r['query'] else '#ffffff', outline=BLUE if name == r['query'] else '#7b8794', width=2)
            label = name + (f'={r["evidence"][name]}' if observed else '')
            c.create_text(x, y, text=label, font=('Segoe UI', 10, 'bold'), fill=INK)
    def draw_bayes(self, width, height):
        r = self.report
        sampling = r['point'] == 3 and r['method'] in ('prior', 'rejection')
        Viewer.draw_network(self, width, height)
        c = self.info_canvas
        width, height = max(c.winfo_width(),350), max(c.winfo_height(),430)
        x = 12
        history = r['history']
        frame = history[min(self.index.get(), len(history)-1)] if history else None
        estimate = r['distribution'][1] if r['distribution'] else None
        caption = 'Estimación final' if r['method'] in ('prior','rejection') else 'Resultado'
        lines = [f'{caption}: {number(estimate)}']
        if 'exact' in r:
            lines.insert(0,f'Exacto: {r["exact"][1]:.6f}')
        bottom = self.card(x, 16, width-x-16, f'P({r["query"]}=1 | evidencia)', lines)
        if sampling:
            row = r['repetitions'][-1]
            self.card(x, bottom, width-x-16, 'ÚLTIMA EJECUCIÓN',
                      [f'Intentos: {row["generated"]}', f'Aceptadas: {row["accepted"]}',
                       f'Error absoluto: {number(row["absolute_error"])}'])
            self.status.configure(text='Compare estimaciones y muestras aceptadas con 1000 y 10000 intentos. Más intentos no garantizan menor error en cada ejecución.')
        elif frame and 'eliminated' in frame:
            if hasattr(self, 'factor_tree'):
                self.factor_label.configure(text=f'Paso {self.index.get()+1} de {len(history)}: eliminar {frame["eliminated"]}. '
                                            f'Variables restantes: {", ".join(frame["variables"]) or "ninguna (constante)"}.')
                self.factor_tree.delete(*self.factor_tree.get_children())
                for row in frame['table']:
                    assignment = ', '.join(f'{name}={value}' for name, value in zip(frame['variables'], row['values'])) or 'Constante'
                    self.factor_tree.insert('', 'end', values=(assignment, number(row['p'])))
            peak = max(step['product_rows'] for step in history)
            self.card(x, bottom, width-x-16, f'PASO {self.index.get()+1} · Eliminar {frame["eliminated"]}',
                      [f'Factor: {", ".join(frame["variables"]) or "constante"}',
                       f'Producto: {frame["product_rows"]} filas', f'Resultante: {len(frame["table"])} filas',
                       f'Mayor producto de la ejecución: {peak} filas'])
            self.status.configure(text='Cada paso suma sobre una variable oculta. Compare el tamaño de los productos al cambiar el orden.')
        else:
            if r.get('utilities'):
                self.card(x, bottom, width-x-16, 'DECISIÓN POR UTILIDAD ESPERADA',
                          [*[f'{a}: {v:.3f}' for a,v in r['utilities'].items()], f'Acción elegida: {r["action"]}'])
            self.status.configure(text='Conjunta → filtrar por evidencia → normalizar → comparar utilidades.' if r['point'] == 1 else
                                  'Amarillo: evidencia. Azul: consulta. Pulse un nodo para consultar su tabla de probabilidades.')

    def inspect_node(self, event):
        if self.report['point'] > 3:
            self.inspect_state(event)
            return
        for name, (x, y) in self.node_positions.items():
            if abs(event.x-x) <= 56 and abs(event.y-y) <= 24:
                node = self.model.by_name[name]
                popup = tk.Toplevel(self.root)
                popup.title(f'CPT - {name}')
                popup.geometry('720x360')
                ttk.Label(popup, text=f'{name} · Tabla de probabilidad condicional', padding=12, font=('Segoe UI',12,'bold')).pack()
                table(popup, [*node['parents'], f'P({name}=0)', f'P({name}=1)'],
                      [(*list(bits), number(1-p), number(p)) for bits,p in node['cpt'].items()])
                break

    def inspect_state(self, event):
        """Detalle local de Bellman; la suma muestra probabilidad, recompensa y continuación."""
        if not hasattr(self, 'grid_geometry'):
            return
        x0,y0,cell = self.grid_geometry
        state = int((event.x-x0)//cell), int((event.y-y0)//cell)
        m, r = self.model, self.report
        if event.x < x0 or event.y < y0 or state not in m.state_set:
            return
        popup = tk.Toplevel(self.root)
        popup.title(f'Bellman · Estado {state}')
        popup.geometry('970x480')
        if state in m.terminals:
            ttk.Label(popup,text=f'Estado terminal. Recompensa al entrar: {m.terminals[state]:g}. V=0; sin acciones.',padding=20).pack()
            return
        index = min(self.index.get(), len(r['history'])-1)
        values = r['values'] if r['point'] == 5 else r['history'][index]
        ttk.Label(popup,text=f'Estado {state} · Q calculado con '+('valores finales' if r['point'] == 5 else f'V{index}')+
                  '. El máximo produce el siguiente valor de Bellman.',wraplength=900,padding=12).pack()
        rows=[]
        totals={}
        for action in m.actions(state):
            contributions=[]
            for nxt,p in m.transitions(state,action):
                reward=m.reward(state,action,nxt)
                continuation=values[f'{nxt[0]},{nxt[1]}']
                contribution=p*(reward+m.discount*continuation)
                contributions.append(contribution)
                rows.append((action,str(nxt),number(p),number(reward),number(continuation),number(contribution)))
            totals[action]=sum(contributions)
        best=max(totals,key=totals.get)
        ttk.Label(popup,text='   ·   '.join(f'Q({a})={v:.5f}' for a,v in totals.items())+f'   →   Acción: {best}',padding=8).pack()
        table(popup,['Acción','Sucesor','Probabilidad','Recompensa','V(siguiente)','Aporte a Q'],rows)

    def draw_mdp(self, width, height):
        c, m, r = self.canvas, self.model, self.report
        trajectory = r['point'] == 5 and self.mode.get() == 'Trayectoria'
        if r['point'] == 5:
            for widget in [*self.playback_buttons, self.slider]:
                widget.configure(state='normal' if trajectory else 'disabled')
        index = min(self.index.get(), self.last_frame())
        values = r['values'] if r['point'] == 5 else r['history'][index]
        cell = min((width-50)/m.width, (height-100)/m.height, 95)
        x0, y0 = (width-m.width*cell)/2, max(40,(height-m.height*cell)/2)
        c.create_text(20,16,text='MAPA DEL DRON',anchor='nw',font=('Segoe UI',10,'bold'),fill=INK)
        self.grid_geometry = x0,y0,cell
        policy = {s: r['policy'][f'{s[0]},{s[1]}'] for s in m.states} if r['point'] == 5 else {}
        scale = max(1, max(abs(v) for v in values.values()))
        for y, row in enumerate(m.grid):
            for x, symbol in enumerate(row):
                state, key = (x, y), f'{x},{y}'
                px, py = x0+x*cell, y0+y*cell
                if symbol == '#':
                    fill, label = '#34463f', 'MURO'
                elif state in m.terminals:
                    fill = '#b8daa8' if symbol == 'G' else '#e7aaa0'
                    label = f'{"DESCARGA" if symbol == "G" else "PÉRDIDA"}\nR={m.terminals[state]:g}\nV=0'
                else:
                    v = values[key]
                    intensity = int(min(90, abs(v)/scale*90))
                    fill = f'#{230-intensity:02x}{240-intensity//3:02x}{226-intensity:02x}' if v >= 0 else '#edd0bc'
                    label = f'{"INICIO" if symbol == "S" else "RIESGO" if symbol == "R" else ""}\n{v:.3f}\n{ARROWS[policy.get(state)]}'
                c.create_rectangle(px, py, px+cell, py+cell, fill=fill, outline='#a3b6a6')
                if symbol == 'R':
                    c.create_rectangle(px+3,py+3,px+cell-3,py+cell-3,outline='#f08c46',width=3)
                if symbol == '#':
                    for offset in (.25,.5,.75):
                        c.create_line(px,py+cell*offset,px+cell,py+cell*offset,fill='#526271')
                if r['point'] == 5 and state not in m.terminals and symbol != '#':
                    heading = 'INICIO' if symbol == 'S' else 'RIESGO' if symbol == 'R' else ''
                    c.create_text(px+cell/2, py+cell*.24, text=f'{heading}\n{values[key]:.3f}', fill=INK, font=('Segoe UI',9))
                    c.create_text(px+cell/2, py+cell*.68, text=ARROWS[policy.get(state)], fill=BLUE, font=('Segoe UI',25,'bold'))
                else:
                    c.create_text(px+cell/2, py+cell/2, text=label, fill='white' if symbol == '#' else INK, font=('Segoe UI', 10, 'bold'))
        if trajectory:
            path = r['trajectory']['path'][:index+1]
            coords = [(x0+(x+.5)*cell, y0+(y+.5)*cell) for x, y in path]
            if len(coords) > 1:
                c.create_line(*[v for xy in coords for v in xy], fill='#2979ac', width=3)
            px, py = coords[-1]
            c.create_oval(px-10, py-10, px+10, py+10, fill='#246da0', outline='white', width=2)
            for dx,dy in ((-13,-13),(13,-13),(-13,13),(13,13)):
                c.create_line(px,py,px+dx,py+dy,fill=INK,width=2)
                c.create_oval(px+dx-5,py+dy-5,px+dx+5,py+dy+5,outline=BLUE,width=2)
        x, width = 12, 350
        bottom=self.card(x,16,width-x-12,'MODELO DEL DRON',
                         [f'Ruido total: {m.noise:g}',f'Recompensa por paso: {m.living_reward:g}',f'Descuento: {m.discount:g}'])
        bottom = self.card(x,bottom,width-x-12,'ITERACIÓN DE VALORES',
                  [f'Convergió: {"Sí" if r["converged"] else "No"}',f'Barridos: {r["iterations"]}',f'V final inicio: {r["start_value"]:.4f}'])
        self.card(x,bottom,width-x-12,'LEYENDA',
                  ['Verde / rojo: valor positivo / negativo', *(['Flechas: acción de la política'] if r['point'] == 5 else []),
                   'DESCARGA / PÉRDIDA: estados terminales', 'Borde naranja: zona de riesgo'])
        if trajectory:
            text = f'Paso {index} de {self.last_frame()} | Una trayectoria, no el valor esperado | Finalizó: {r["trajectory"]["finished"]}'
        elif r['point'] == 5:
            text = 'Política devuelta por extract_policy con los valores finales. Pulse una celda para revisar sus acciones.'
        else:
            delta = r['deltas'][index-1] if index else 0
            text = f'Barrido {index} | Cambio máximo: {delta:.8g} | Pulse una celda para ver su cálculo de Bellman.'
        self.status.configure(text=text)


def show(report, model, frame_time=0.3):
    try:
        root = tk.Tk()
    except tk.TclError as error:
        raise ValueError('No fue posible abrir Tk. Use -t para ver los resultados en texto.') from error
    Viewer(root, report, model, frame_time)
    root.mainloop()
