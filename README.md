# miniheroes-v1.0.0
automation

tasks:
Emulator start, Stop
Verify start, Verify stop
Save failed, Save completed
Load saved (done, failed)
Install game 3 packages
Clear data game
Start gane
Tap and tap player
Repeat tap 0.1s
Email login step with verification through current image
Gmail create
Gmail code fetcher
Accurate taps list with accurate time
Save gmails

2nd feature Level up account ----
Start emulators at a time
Clear data
Start game
Login this time
Start a complete level up process to lvl 35
And clear data agar game

completed functions------------------------------------

init_ld_list() -> List[str]
→ LDPlayer se saare created emulator indexes nikaal ke ldplayer_indexes.txt file me save karta hai aur list return karta hai.

load_indexes() -> List[str]
→ Index file se saved emulator indexes read karke list return karta hai.

delete_index(index: str) -> bool
→ Given emulator index ko file se delete karta hai aur success / failure return karta hai.

pop_next_index() -> str | None
→ FIFO order me next available emulator index uthata hai aur file se hata deta hai, empty ho to None return karta hai.

get_all_ldplayer_emulators() -> List[Dict]
→ Saare LDPlayer emulators (running + stopped) ka structured data return karta hai.

get_running_ldplayer_emulators() -> List[Dict]
→ Sirf currently running LDPlayer emulators ka data return karta hai.

get_stopped_ldplayer_emulators() -> List[Dict]
→ Sirf stopped / idle LDPlayer emulators ka data return karta hai.

get_ldplayer_by_index(index: str) -> Dict | None
→ Given emulator index ka LDPlayer metadata return karta hai, exist na kare to None.

get_running_emulators() -> List[str]
→ Running LDPlayer emulators ko ADB-style format (127.0.0.1:port) me list karke return karta hai.

start_emulator_indices(indices: List[int | str], sleep_sec: float = 1.5) -> None
→ Given emulator indexes ko ldconsole ke through start karta hai, har launch ke beech delay ke saath.

stop_emulator_indices(indices: List[int | str], sleep_sec: float = 1.0) -> None
→ Given emulator indexes ko ldconsole ke through safely stop karta hai.

list_emulator_indices() -> List[int]
→ LDPlayer me jitne emulators create hue hain unke indexes ki sorted list return karta hai.

end----------------------------------------------------