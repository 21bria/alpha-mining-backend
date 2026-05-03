def build_iup_clause(iup_filter, alias=None, request=None):
    try:
        # AUTO DETECT PARAM
        # kalau dipanggil:
        # build_iup_clause(request, iup_filter, "s")
        if hasattr(iup_filter, "user"):
            req = iup_filter
            iup_filter = alias
            alias = request
            request = req

        # kalau alias tidak ada → skip
        if not alias:
            return "", []

        
        # 1. AMBIL ALLOWED IUP USER
        
        allowed_iups = None

        if request and not request.user.is_superuser:
            allowed_iups = list(
                request.user.iup_access.filter(is_active=True)
                .values_list("iup_id", flat=True)
            )

        
        # 2. PARSE INPUT (LOGIC LAMA YANG DIPERTAHANKAN)
        
        if not iup_filter:
            iup_ids = allowed_iups
        else:
            if isinstance(iup_filter, (list, tuple, set)):
                raw_ids = list(iup_filter)
            else:
                raw = str(iup_filter).strip()
                raw = raw.strip("()[]{}")
                raw_ids = [x.strip() for x in raw.split(",") if x.strip()]

            iup_ids = []
            for x in raw_ids:
                sx = str(x).strip().strip("'").strip('"')
                if sx.isdigit():
                    iup_ids.append(int(sx))

            # filter dengan allowed
            if allowed_iups is not None:
                iup_ids = [i for i in iup_ids if i in allowed_iups]

        
        # 3. PROTEKSI
        
        if allowed_iups is not None and not iup_ids:
            return " AND 1=0", []

        if not iup_ids:
            return "", []

        placeholders = ",".join(["%s"] * len(iup_ids))
        return f" AND {alias}.iup_id IN ({placeholders})", iup_ids

    except Exception:
        return "", []