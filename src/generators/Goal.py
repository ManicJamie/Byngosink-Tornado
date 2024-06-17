LangCode = str
"""An ISO 639 language code (eg. "en", "cn", "jp"...)"""

class Goal():
    id: str
    name: str
    translations: dict[LangCode, str]
    # Generation info
    exclusions: list[str]
    tiebreaker: bool = False
    cost: float = 0
    weight: float = 1
    
    def __init__(self, src: dict, id: str) -> None:
        self.id = id
        self.translations = dict()
        self.exclusions = []
        
        for key, val in src.items():
            setattr(self, key, val)
        try:
            _ = (self.id, self.name)
        except AttributeError as e:
            raise AttributeError(f"Goal {e.obj} constructed missing required field {e.name}.") from e
