from core.permissions import user_allowed_iup_ids

GLOBAL_ROLES = ["SYSTEM", "MANAGEMENT", "GLOBAL_VIEWER"]

# def build_iup_clause(iup_filter, alias=None, request=None):
#     try:
#         if hasattr(iup_filter, "user"):
#             req = iup_filter
#             iup_filter = alias
#             alias = request
#             request = req

#         if not alias:
#             return "", []

#         allowed_iups = None

#         if request and not request.user.is_superuser:
#             allowed_iups = list(
#                 request.user.iup_access.filter(is_active=True)
#                 .values_list("iup_id", flat=True)
#             )

#             user_role = getattr(request.user, "role", "")
#             user_role = str(user_role).upper()

#             global_roles = ["SYSTEM", "MANAGEMENT", "GLOBAL_VIEWER"]

#             # SITE_USER / non-global dipaksa ke active/default IUP
#             if user_role not in global_roles:
#                 default_iup_id = getattr(request.user, "active_iup_id", None) or getattr(request.user, "default_iup_id", None)

#                 if default_iup_id:
#                     iup_filter = default_iup_id

#         if not iup_filter:
#             iup_ids = allowed_iups
#         else:
#             if isinstance(iup_filter, (list, tuple, set)):
#                 raw_ids = list(iup_filter)
#             else:
#                 raw = str(iup_filter).strip()
#                 raw = raw.strip("()[]{}")
#                 raw_ids = [x.strip() for x in raw.split(",") if x.strip()]

#             iup_ids = []
#             for x in raw_ids:
#                 sx = str(x).strip().strip("'").strip('"')
#                 if sx.isdigit():
#                     iup_ids.append(int(sx))

#             if allowed_iups is not None:
#                 iup_ids = [i for i in iup_ids if i in allowed_iups]

#         if allowed_iups is not None and not iup_ids:
#             return " AND 1=0", []

#         if not iup_ids:
#             return "", []

#         placeholders = ",".join(["%s"] * len(iup_ids))
#         return f" AND {alias}.iup_id IN ({placeholders})", iup_ids

#     except Exception:
#         return "", []

def build_iup_clause(iup_filter, alias=None, request=None):
    try:
        if hasattr(iup_filter, "user"):
            req = iup_filter
            iup_filter = alias
            alias = request
            request = req

        if not alias:
            return "", []

        allowed_iups = None

        if request and not request.user.is_superuser:
            user = request.user

            allowed_iups = list(user_allowed_iup_ids(user))

            if not allowed_iups:
                return " AND 1=0", []

            role = str(getattr(user, "role", "")).upper()

            # selain management/system/global
            # otomatis pakai IUP user login
            if role not in GLOBAL_ROLES and not iup_filter:

                active_iup = (
                    getattr(user, "active_iup_id", None)
                    or getattr(user, "iup_id", None)
                )

                if active_iup:
                    iup_filter = active_iup
                else:
                    iup_filter = allowed_iups[0]

        if not iup_filter:
            iup_ids = allowed_iups
        else:
            raw_ids = (
                list(iup_filter)
                if isinstance(iup_filter, (list, tuple, set))
                else str(iup_filter).split(",")
            )

            iup_ids = []

            for x in raw_ids:
                sx = str(x).strip().strip("'").strip('"')

                if sx.isdigit():
                    iup_ids.append(int(sx))

            if allowed_iups is not None:
                iup_ids = [i for i in iup_ids if i in allowed_iups]

        if allowed_iups is not None and not iup_ids:
            return " AND 1=0", []

        if not iup_ids:
            return "", []

        placeholders = ",".join(["%s"] * len(iup_ids))

        return f" AND {alias}.iup_id IN ({placeholders})", iup_ids

    except Exception:
        return " AND 1=0", []