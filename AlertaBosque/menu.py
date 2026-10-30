"""Menú Textual. El cálculo se ejecuta fuera del hilo de la interfaz."""
import json
import subprocess
import sys
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Footer, Select, Input, Label, Button, RichLog, Static
from textual import work

ROOT = Path(__file__).resolve().parent
POINTS = ['Probabilidades y utilidad', 'Enumeración', 'Eliminación y muestreo',
          'Iteración de valores', 'Política del dron']
METHODS = [('A priori','prior'), ('Rechazo','rejection'),
           ('Eliminación de variables','elimination')]


class WorkshopMenu(App):
    TITLE = 'Alerta Bosque - Taller 3'
    CSS = '''
    Screen { background: #0d1117; color: #e6edf3; }
    .title-bar { height: 3; padding: 0 2; background: #161b22; border-bottom: solid #30363d; content-align: left middle; }
    #shell { height: 1fr; }
    .panel { padding: 1; border: solid #30363d; background: #0d1117; }
    #points { width: 30; min-width: 26; }
    #scenario { width: 1fr; }
    #settings { width: 36; }
    #bayes-options, #mdp-options, #sample-options { height: auto; }
    Label { margin-top: 1; color: #58a6ff; }
    .point-card { width: 100%; height: 4; margin-bottom: 1; background: #161b22; border: solid #21262d; }
    .active-point { border: solid #f0c040; background: #1c2836; }
    .point-card:focus { border: solid #58a6ff; background: #1c2128; }
    Input { height: 3; border: solid #21262d; background: #0a0f16; }
    #point { display: none; }
    #purpose { height: auto; min-height: 6; padding: 1; border: solid #21262d; background: #0a0f16; margin-top: 1; }
    .section { color: #f0c040; text-style: bold; }
    Select, Input { width: 100%; }
    #buttons { height: 3; margin: 0 1; }
    #buttons Button { min-width: 12; padding: 0 2; }
    #run { background: #58a6ff; color: #0d1117; border: tall #58a6ff; }
    #run:hover, #run:focus { background: #79b8ff; border: tall #79b8ff; }
    RichLog { height: 3; border: solid #30363d; margin: 0 1; }
    '''
    BINDINGS = [('q', 'quit', 'Salir'), ('r', 'run', 'Ejecutar')]

    def compose(self) -> ComposeResult:
        yield Static('ALERTA BOSQUE  ·  Taller 3 — Razonamiento bajo incertidumbre',classes='title-bar')
        with Horizontal(id='shell'):
            with VerticalScroll(id='points', classes='panel'):
                yield Label('EJERCICIOS', classes='section')
                yield Select([(p,i+1) for i,p in enumerate(POINTS)],value=1,id='point',allow_blank=False)
                for i, point in enumerate(POINTS,1):
                    yield Button(f'{i}. {point}', id=f'point-{i}', classes='point-card')
                yield Static('Punto 6\nAnálisis de los resultados anteriores.')
            with VerticalScroll(id='scenario', classes='panel'):
                yield Label('ESCENARIO', classes='section')
                yield Select([], id='layout')
                yield Static('', id='purpose')
                with VerticalScroll(id='bayes-options'):
                    yield Label('Caso de evidencia')
                    yield Select([], id='case')
                    yield Label('Variable de consulta')
                    yield Input('Incendio', id='query')
                    yield Label('Evidencia personalizada (opcional)')
                    yield Input('', placeholder='Alarma=1,Falla=0', id='evidence')
                    yield Label('Método de inferencia', id='method-label')
                    yield Select(METHODS,value='prior',id='method',allow_blank=False)
                    yield Static('', id='inference-help')
                    yield Label('Orden de eliminación',id='order-label')
                    yield Select([('Topológico','forward'),('Inverso','reverse')],value='forward',id='order',allow_blank=False)
                with VerticalScroll(id='mdp-options'):
                    yield Label('Vacío: usar los parámetros del mapa')
                    yield Label('Ruido total')
                    yield Input('', id='noise')
                    yield Label('Recompensa por movimiento')
                    yield Input('', id='living-reward')
                    yield Label('Factor de descuento')
                    yield Input('', id='discount')
            with VerticalScroll(id='settings', classes='panel'):
                yield Label('EJECUCIÓN', classes='section')
                with VerticalScroll(id='sample-options'):
                    yield Label('Intentos de muestreo')
                    yield Input('10000',id='samples')
                    yield Label('Repeticiones')
                    yield Input('1',id='repeat')
                yield Label('Semilla',id='seed-label')
                yield Input('7',id='seed')
                yield Label('Visualización')
                yield Select([('Gráfica','graphics'),('Texto','text')],value='graphics',id='display',allow_blank=False)
        with Horizontal(id='buttons'):
            yield Button('Ejecutar', id='run', variant='primary')
            yield Button('Salir', id='quit')
        yield RichLog(id='log', wrap=True)
        yield Footer()

    def on_mount(self):
        self.update_layouts()

    def update_layouts(self):
        point = self.query_one('#point', Select).value
        for i in range(1,6):
            self.query_one(f'#point-{i}',Button).set_class(i==point,'active-point')
        self.query_one('#bayes-options').display = point <= 3
        self.query_one('#mdp-options').display = point > 3
        for key in ('method','method-label'):
            self.query_one(f'#{key}').display = point == 3
        self.update_method_options()
        folder = 'bayes' if point <= 3 else 'mdp'
        if getattr(self, '_folder', None) == folder:
            return
        self._folder = folder
        options = sorted(p.stem for p in (ROOT / 'layouts' / folder).glob('*.json'))
        widget = self.query_one('#layout', Select)
        widget.set_options([(x, x) for x in options])
        widget.value = 'sensor_basico' if folder == 'bayes' else 'cuadricula'

    def update_method_options(self):
        self.sync_inference_options()
        point = self.query_one('#point',Select).value
        method = self.query_one('#method',Select).value
        sampling = point == 3 and method in ('prior','rejection')
        for key in ('order','order-label'):
            self.query_one(f'#{key}').display = point == 3 and method == 'elimination'
        self.query_one('#sample-options').display = sampling
        for key in ('seed','seed-label'):
            self.query_one(f'#{key}').display = sampling or point == 5

    def sync_inference_options(self):
        """Solo ofrece combinaciones compatibles, sin borrar evidencia del usuario."""
        point = self.query_one('#point', Select).value
        method = self.query_one('#method', Select)
        case = self.query_one('#case', Select)
        evidence = self.query_one('#evidence', Input)
        cases = getattr(self, '_cases', {})
        has_evidence = bool(evidence.value.strip() or cases.get(case.value, {}))
        options = [option for option in METHODS
                   if not (point == 3 and has_evidence and option[1] == 'prior')]
        if getattr(self, '_method_choices', None) != options:
            selected = method.value
            self._method_choices = options
            method.set_options(options)
            method.value = selected if selected in [v for _, v in options] else 'rejection'
        prior = point == 3 and method.value == 'prior'
        choices = [name for name, values in cases.items() if not prior or not values]
        if getattr(self, '_case_choices', None) != choices:
            selected = case.value
            self._case_choices = choices
            case.set_options([(name, name) for name in choices])
            if choices:
                case.value = selected if selected in choices else choices[0]
        evidence.disabled = prior
        help_text = self.query_one('#inference-help', Static)
        help_text.display = point == 3
        help_text.update('A priori usa solo sin evidencia. Para observar evidencia, elija otro método.'
                         if prior else 'Con evidencia, A priori no está disponible. Para usarlo, borre la evidencia personalizada y elija sin_evidencia.')

    def on_input_changed(self, event):
        if event.input.id == 'evidence' and list(self.query('#inference-help')):
            self.update_method_options()

    def on_select_changed(self, event):
        if not list(self.query('#point')):
            return  # The menu may already be unmounting.
        if event.select.id == 'point':
            self.query_one('#evidence', Input).value = ''
            self.update_layouts()
        elif event.select.id in ('method', 'case'):
            self.update_method_options()
        elif event.select.id == 'layout' and isinstance(event.value, str) and event.value == event.select.value:
            point = self.query_one('#point', Select).value
            folder = 'bayes' if point <= 3 else 'mdp'
            path = ROOT/'layouts'/folder/f'{event.value}.json'
            if not path.is_file():
                return  # Ignore queued events from the previous phase.
            data = json.loads(path.read_text(encoding='utf-8'))
            self.query_one('#evidence', Input).value = ''
            if point <= 3:
                query = self.query_one('#query', Input)
                if query.value not in [node['name'] for node in data['nodes']]:
                    query.value = 'Incendio'
            else:
                for key in ('noise', 'living-reward', 'discount'):
                    self.query_one(f'#{key}', Input).value = ''
            self.query_one('#purpose',Static).update(data['name']+'\n\n'+data['description'])
            self._cases = data.get('cases', {'sin_evidencia': {}})
            self._case_choices = None
            # Un escenario nuevo comienza sin evidencia predefinida.
            self.query_one('#case', Select).clear()
            self.update_method_options()

    def on_button_pressed(self, event):
        if event.button.id.startswith('point-'):
            self.query_one('#point',Select).value = int(event.button.id.split('-')[1])
        elif event.button.id == 'quit':
            self.exit()
        else:
            self.action_run()

    def action_run(self):
        button = self.query_one('#run', Button)
        if button.disabled:
            return
        command = [sys.executable, '-X', 'utf8', str(ROOT / 'main.py')]
        point = self.query_one('#point',Select).value
        method = self.query_one('#method',Select).value
        sampling = point == 3 and method in ('prior','rejection')
        selections = ['point','layout'] + (['case'] if point <= 3 else []) + (['method'] if point == 3 else [])
        if point == 3 and method == 'elimination':
            selections.append('order')
        for key in selections:
            value = self.query_one(f'#{key}', Select).value
            if not isinstance(value, (str, int)):
                self.query_one('#log', RichLog).write('Seleccione un escenario.')
                return
            command += [f'--{key}', str(value)]
        inputs = ['query','evidence'] if point <=3 else ['noise','living-reward','discount']
        if sampling:
            inputs += ['samples','repeat']
        if sampling or point == 5:
            inputs.append('seed')
        for key in inputs:
            value = self.query_one(f'#{key}', Input).value.strip()
            if value:
                command += [f'--{key}', value]
        mode = self.query_one('#display', Select).value
        if mode != 'graphics':
            command += ['-t']
        button.disabled = True
        if mode != 'graphics':
            self.run_terminal(command)
            return
        self.query_one('#log', RichLog).write('Ejecutando. Cierre la ventana gráfica para volver a ejecutar.')
        self.run_process(command)

    def run_terminal(self, command):
        try:
            with self.suspend():
                try:
                    subprocess.run(command, cwd=ROOT)
                except (OSError, KeyboardInterrupt) as error:
                    print(f'No se completó la ejecución: {error}')
                try:
                    input('\nPulse Enter para volver al menú...')
                except (EOFError, KeyboardInterrupt):
                    pass
        finally:
            self.query_one('#run', Button).disabled = False

    @work(thread=True)
    def run_process(self, command):
        try:
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
            self.call_from_thread(self.query_one('#log', RichLog).write, result.stdout + result.stderr)
        except OSError as error:
            self.call_from_thread(self.query_one('#log', RichLog).write, str(error))
        finally:
            self.call_from_thread(setattr, self.query_one('#run', Button), 'disabled', False)


def launch():
    WorkshopMenu().run()


if __name__ == '__main__':
    launch()
