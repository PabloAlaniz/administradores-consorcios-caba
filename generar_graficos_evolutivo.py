"""
Genera los gráficos de evolución del padrón a partir de `data/evolutivo/`.

Produce en `docs/img/`:
- `evolucion_padron.png`: total de administradores, matrículas activas y
  sin actualizar, mes a mes.
- `evolucion_concentracion.png`: % de consorcios en manos del top 1/5/10%
  e índice de Gini, mes a mes.

Con un solo snapshot dibuja los puntos iniciales; las tendencias aparecen
a medida que se acumulan cortes mensuales.

Uso:
    python generar_graficos_evolutivo.py
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

EVOLUTIVO_DIR = os.path.join('data', 'evolutivo')
IMG_DIR = os.path.join('docs', 'img')


def _guardar(fig, nombre, img_dir):
    path = os.path.join(img_dir, nombre)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  ✓ {path}')
    return path


def grafico_padron(resumen, img_dir=IMG_DIR):
    """Evolución del tamaño y estado del padrón."""
    fig, ax = plt.subplots(figsize=(9, 5))
    series = [
        ('total_administradores', 'Total registrados', 'o-'),
        ('matriculas_activas', 'Activas', 's-'),
        ('matriculas_sin_actualizar', 'Sin actualizar', '^-'),
    ]
    for col, etiqueta, marca in series:
        if col in resumen.columns:
            ax.plot(resumen['snapshot'], resumen[col], marca, label=etiqueta)
    ax.set_title('Evolución del padrón de administradores')
    ax.set_xlabel('Snapshot (mes)')
    ax.set_ylabel('Administradores')
    ax.legend()
    ax.grid(alpha=0.3)
    return _guardar(fig, 'evolucion_padron.png', img_dir)


def grafico_concentracion(resumen, img_dir=IMG_DIR):
    """Evolución de la concentración del mercado (top-N% y Gini)."""
    fig, ax = plt.subplots(figsize=(9, 5))
    for col, etiqueta, marca in [
        ('pct_top_1', 'Top 1%', 'o-'),
        ('pct_top_5', 'Top 5%', 's-'),
        ('pct_top_10', 'Top 10%', '^-'),
    ]:
        if col in resumen.columns:
            ax.plot(resumen['snapshot'], resumen[col], marca, label=etiqueta)
    ax.set_ylabel('% de consorcios concentrados')
    ax.set_xlabel('Snapshot (mes)')
    ax.set_ylim(0, 100)
    ax.grid(alpha=0.3)

    if 'gini' in resumen.columns and resumen['gini'].notna().any():
        ax2 = ax.twinx()
        ax2.plot(resumen['snapshot'], resumen['gini'], 'd--', color='gray', label='Gini (der.)')
        ax2.set_ylabel('Índice de Gini')
        ax2.set_ylim(0, 1)
        lineas1, etiquetas1 = ax.get_legend_handles_labels()
        lineas2, etiquetas2 = ax2.get_legend_handles_labels()
        ax.legend(lineas1 + lineas2, etiquetas1 + etiquetas2, loc='lower right')
    else:
        ax.legend(loc='lower right')

    ax.set_title('Evolución de la concentración del mercado')
    return _guardar(fig, 'evolucion_concentracion.png', img_dir)


def main(evolutivo_dir=EVOLUTIVO_DIR, img_dir=IMG_DIR):
    resumen_path = os.path.join(evolutivo_dir, 'resumen.csv')
    if not os.path.exists(resumen_path):
        raise SystemExit(
            f'No se encontró {resumen_path}. Generalo primero con: python generar_evolutivo.py'
        )

    sns.set_theme(style='whitegrid')
    os.makedirs(img_dir, exist_ok=True)
    resumen = pd.read_csv(resumen_path)

    grafico_padron(resumen, img_dir)
    grafico_concentracion(resumen, img_dir)

    if len(resumen) < 2:
        print('\nNota: hay un solo snapshot; los gráficos muestran puntos y las tendencias aparecen desde el segundo corte.')
    print(f'\nListo: gráficos evolutivos → {img_dir}/')


if __name__ == '__main__':
    main()
