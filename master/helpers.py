def user_default_iup_id(user):
    return getattr(user, "default_iup_id", None)

def user_allowed_iup_ids(user):
    ids = set(getattr(user, "allowed_iup_ids", None) or [])
    did = getattr(user, "default_iup_id", None)
    if did:
        ids.add(did)
    return list(ids)