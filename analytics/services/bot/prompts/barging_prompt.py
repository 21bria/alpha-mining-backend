# prompts/barging_prompt.py

def barging_review_prompt(data, language="id"):

    lang = "English" if language == "en" else "Bahasa Indonesia"

    return f"""
Kamu adalah Senior Mining Barging & Selling Analyst.

Gunakan bahasa:
{lang}

Data:
{data}

Tugas:
Buat review profesional terkait:

- Barging performance
- Selling performance
- Average MT per barge
- Loading activity
- Floating barge analysis
- Ore composition LIM vs SAP
- COA vs internal grade comparison
- Grade deviation analysis
- Potential operational issue
- Recommendation

Gunakan markdown.

Format:

## Executive Summary

## Barging Overview

## Selling Overview

## Loading Performance

## COA vs Internal Grade

## Key Operational Issue

## Recommendation
"""