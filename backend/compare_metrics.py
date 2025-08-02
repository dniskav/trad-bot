from metrics_logger import MetricsLogger

def print_summary(version=None):
    logger = MetricsLogger(filepath="logs/trades.csv")
    metrics = logger.compute_metrics(version_filter=version)
    label = version if version else "todas"
    print(f"\n--- Métricas para versión: {label} ---")
    if not metrics:
        print("No hay trades registrados.")
        return
    for k, v in metrics.items():
        print(f"{k}: {v}")
    print("-----------------------------------\n")

if __name__ == "__main__":
    # Comparar todas y luego versión específica
    print_summary()  # todo
    # Ejemplo: ajustar la etiqueta según lo que uses
    print_summary("v1-sma-cross")