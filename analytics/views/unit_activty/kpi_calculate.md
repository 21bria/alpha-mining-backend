op / working = EWH
st / standby = STB + SUPPORT + WX + SLP
mt / maintenance = PM + BD
bd = BD
time = jumlah unit-date × 24 jam
fuel = total fuel per unit dan tanggal

===========================================

Rumus KPI:

MA = EWH / (EWH + PM + BD) × 100
PA = (EWH + STB + SUPPORT + WX + SLP) / Total Time × 100
UA = EWH / (EWH + STB + SUPPORT + WX + SLP) × 100
EU = EWH / Total Time × 100

Contoh sederhana:

EWH = 10 jam
Standby = 5 jam
Maintenance = 2 jam
BD = 1 jam
Total Time = 24 jam

Maka:

MA = 10 / (10 + 2) × 100 = 83.33%
PA = (10 + 5) / 24 × 100 = 62.50%
UA = 10 / (10 + 5) × 100 = 66.67%
EU = 10 / 24 × 100 = 41.67%
============================================

Descriptions :

**** MA ******

MA — Mechanical Availability
Persentase kesiapan alat dari sisi mekanik.
Mengukur: 
“Saat alat tidak rusak/maintenance, berapa persen alat siap dipakai?”

Rumus:
MA = EWH / (EWH + PM + BD) × 100

Keterangan:
EWH = jam kerja alat
PM  = preventive maintenance
BD  = breakdown

Contoh:

Working = 20 jam
Maintenance = 4 jam

Maka:

MA = 20 / (20 + 4) × 100
MA = 83.33%


**** PA ******

PA — Physical Availability
Persentase ketersediaan fisik alat terhadap total waktu.

Mengukur:
“Dari total waktu tersedia, berapa persen alat physically available?”

Rumus:
PA = (EWH + STB + SUPPORT + WX + SLP) / Total Time × 100

Keterangan:

STB = standby
WX  = weather
SLP = slippery
SUPPORT = support activity

Contoh:

Working = 10 jam
Standby = 8 jam
Total Time = 24 jam

PA = (10 + 8) / 24 × 100
PA = 75%

**** UA ******

UA — Use of Availability

Efektivitas penggunaan alat saat alat tersedia.

Mengukur:
“Saat alat available, benar-benar dipakai kerja berapa persen?”

Rumus:
UA = EWH / (EWH + STB + SUPPORT + WX + SLP) × 100

Contoh:

Working = 10 jam
Standby = 5 jam

UA = 10 / (10 + 5) × 100
UA = 66.67%

Kalau UA rendah:
alat tersedia
tapi banyak idle/standby

**** EU ******

EU — Effective Utilization

Efektivitas pemanfaatan alat terhadap total waktu kalender.

Mengukur:

“Dari total 24 jam sehari, berapa persen benar-benar produktif?”

Rumus:
EU = 10 / 24 × 100 = 41.67%

Contoh:
Working = 10 jam
Total Time = 24 jam
EU = 41.67%

EU biasanya paling kecil karena dibanding total waktu penuh.

=======================================
Kesimpulan sederhana
KPI	Fokus
MA	kesehatan alat
PA	alat tersedia
UA	alat dipakai
EU	alat produktif real
=========================================