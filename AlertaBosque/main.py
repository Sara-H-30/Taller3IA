"""python main.py abre el menú. --help muestra la ejecución directa."""
import argparse
import sys
from runner import run
from view.text_display import display


def parser():
    p = argparse.ArgumentParser(description='Taller 3 - Alerta Bosque')
    p.add_argument('-p', '--point', type=int, choices=range(1, 6), default=1)
    p.add_argument('-l', '--layout', default=None)
    p.add_argument('--case', default='sin_evidencia')
    p.add_argument('--query', default='Incendio')
    p.add_argument('--evidence', default=None, help='Sustituye el caso: Alarma=1,Falla=0; cadena vacía sin evidencia')
    p.add_argument('-a', '--method', choices=['elimination', 'prior', 'rejection'], default='prior')
    p.add_argument('--order', default='forward', help='forward, reverse o lista de variables ocultas separadas por coma')
    p.add_argument('-n', '--samples', type=int, default=10000)
    p.add_argument('--repeat', type=int, default=1)
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--noise', type=float, default=None)
    p.add_argument('--living-reward', type=float, default=None)
    p.add_argument('--discount', type=float, default=None)
    p.add_argument('--tolerance', type=float, default=1e-8)
    p.add_argument('--iterations', type=int, default=1000)
    p.add_argument('--max-steps', type=int, default=100)
    p.add_argument('-x', '--frame-time', type=float, default=0.3)
    p.add_argument('-t', '--text', action='store_true', help='Resultados y tablas en la terminal, sin ventana gráfica')
    return p


def execute(args):
    args.layout = args.layout or ('sensor_basico' if args.point <= 3 else 'cuadricula')
    if args.repeat < 1 or args.samples < 1 or args.max_steps < 1 or args.frame_time <= 0:
        raise ValueError('Repeticiones, muestras, pasos y tiempo de cuadro deben ser positivos')
    report, model = run(args)
    if args.text:
        display(report, model)
    else:
        from view.graphics_display import show
        show(report, model, args.frame_time)
    return report


def main():
    if len(sys.argv) == 1:
        from menu import launch
        launch()
        return
    p = parser()
    args = p.parse_args()
    try:
        execute(args)
    except (ValueError, KeyError, OSError, NotImplementedError) as error:
        p.error(str(error))


if __name__ == '__main__':
    main()
