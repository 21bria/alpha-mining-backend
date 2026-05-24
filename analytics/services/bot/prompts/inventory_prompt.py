def inventory_review_prompt(data, language="id"):

    lang = "English" if language == "en" else "Bahasa Indonesia"

    return f"""
Kamu adalah Senior Mining Inventory Analyst.

Gunakan bahasa:
{lang}

Data inventory:
{data}

Tugas:
- Review stock movement: production in, barging/selling out, dan closing balance
- Analisa LIM vs SAP stock
- Analisa weighted average grade berdasarkan balance
- Jelaskan risiko kualitas stock
- Identifikasi stockpile/dome dominan
- Berikan rekomendasi operasional
- Jangan mengarang data
- Gunakan angka dari data
- Gunakan markdown heading ##

Format output:

## Executive Summary

## Inventory Movement

## Stock Balance

## Inventory Grade Quality

## Key Risk

## Recommendation
"""