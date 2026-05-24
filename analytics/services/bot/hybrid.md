Pakai hybrid mode:

1. Fast summary / quick analysis → streaming langsung

chat-stream
→ query summary
→ AI stream
→ user langsung lihat jawaban

2. Heavy analysis / PDF / forecast / anomaly → Celery

chat
→ create task
→ celery proses
→ polling result

Cara bedakannya di request:

body: {
  message: userText,
  mode: 'stream' // atau 'async'
}

Atau otomatis dari backend:

HEAVY_INTENTS = [
    "operational_analysis",
    "anomaly_review",
    "forecast_review",
    "prediction_review",
]

HASIL
Fast Prompt
data hujan bulan april 2026

→ streaming realtime

Heavy Analysis
Kenapa produksi turun saat hujan tinggi?

→ Celery async