import csv
import os
from dataclasses import dataclass, asdict
from typing import List, Optional
import numpy as np

@dataclass
class Trade:
    entry_time: str
    exit_time: Optional[str]
    entry_price: float
    exit_price: Optional[float]
    position: str  # "LONG"
    quantity: float
    pnl: Optional[float]  # profit/loss en unidades de precio
    return_pct: Optional[float]  # porcentaje respecto al capital asumido
    version: str  # etiqueta de versión

class MetricsLogger:
    def __init__(self, filepath="logs/trades.csv"):
        self.filepath = filepath
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        self.trades: List[Trade] = []
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self._fieldnames())
                writer.writeheader()
        else:
            self._load_existing()

    def _fieldnames(self):
        return [
            "entry_time",
            "exit_time",
            "entry_price",
            "exit_price",
            "position",
            "quantity",
            "pnl",
            "return_pct",
            "version",
        ]

    def _load_existing(self):
        with open(self.filepath, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trade = Trade(
                    entry_time=row["entry_time"],
                    exit_time=row["exit_time"] or None,
                    entry_price=float(row["entry_price"]),
                    exit_price=float(row["exit_price"]) if row["exit_price"] else None,
                    position=row["position"],
                    quantity=float(row["quantity"]),
                    pnl=float(row["pnl"]) if row["pnl"] else None,
                    return_pct=float(row["return_pct"]) if row["return_pct"] else None,
                    version=row["version"],
                )
                self.trades.append(trade)

    def record_trade(self, trade: Trade):
        self.trades.append(trade)
        with open(self.filepath, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self._fieldnames())
            writer.writerow(asdict(trade))

    def compute_metrics(self, version_filter: Optional[str] = None):
        trades = [t for t in self.trades if (version_filter is None or t.version == version_filter)]
        if not trades:
            return {}

        profits = []
        returns = []
        for t in trades:
            if t.pnl is not None:
                profits.append(t.pnl)
            if t.return_pct is not None:
                returns.append(t.return_pct)

        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p <= 0]
        win_rate = len(wins) / len(profits) if profits else 0

        gross_win = sum(wins)
        gross_loss = -sum(losses) if losses else 0
        profit_factor = (gross_win / gross_loss) if gross_loss > 0 else float("inf")

        # Equity curve de retornos secuenciales
        eq = [1.0]
        for r in returns:
            eq.append(eq[-1] * (1 + r))
        eq_curve = np.array(eq[1:])
        peak = np.maximum.accumulate(eq_curve)
        drawdowns = (peak - eq_curve) / peak
        max_drawdown = float(np.max(drawdowns)) if len(drawdowns) else 0.0

        avg_return = float(np.mean(returns)) if returns else 0.0
        sharpe = None
        if len(returns) > 1:
            std = float(np.std(returns, ddof=1))
            if std != 0:
                sharpe = (avg_return / std) * np.sqrt(252 * 24 * 60 / 1)  # escala aproximada

        return {
            "total_trades": len(trades),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "avg_return": avg_return,
            "sharpe": sharpe,
        }