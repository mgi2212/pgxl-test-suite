
from typing import Iterable
def checklist_confirm(intro: str, items: Iterable[str]) -> bool:
    print(intro)
    for i, item in enumerate(items, 1):
        print(f"  [{i}] {item}")
    ans = input("Type 'YES' to confirm all steps are complete: ").strip().upper()
    return ans == 'YES'
