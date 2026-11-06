import subprocess
import sys
import argparse
import time
import select

CHATS = [
    "@Perfect_Uss",
    "-1003119628307",
    "-1003566685222",
    "@blahblbla",
    "@Baba_Yaga_World",
    "-1002005100158",
    "-1002139578967",
    "-1003029223847",
    "-1003587834964",
    "@chit_chatter"
]
TARGET_USER = "@You_are_mine_143"

def run_scraper(chat, user, mode, limit):
    cmd = [
        sys.executable, "telegram_dataset_builder.py",
        "--chat", str(chat),
        "--user", str(user),
        "--mode", mode,
        "--limit", str(limit)
    ]
    print(f"\n==================================================")
    print(f" Running Scraper: Chat={chat} | User={user} | Mode={mode}")
    print(f"==================================================")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Increased timeout to 300 seconds (5 minutes) to allow deep history fetches
    IDLE_TIMEOUT = 300
    last_activity = time.time()

    try:
        while True:
            ret = proc.poll()
            rlist, _, _ = select.select([proc.stdout], [], [], 1.0)

            if rlist:
                line = proc.stdout.readline()
                if line:
                    print(line, end='', flush=True)
                    last_activity = time.time()

            if ret is not None:
                break

            if time.time() - last_activity > IDLE_TIMEOUT:
                print(f"\n ⚠️ No progress/activity for {IDLE_TIMEOUT}s. Skipping stuck chat and moving on...")
                proc.kill()
                proc.wait()
                break
    except Exception as e:
        print(f"\n ❌ Error monitoring process: {e}")
        proc.kill()
        proc.wait()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="forward", choices=["back", "forward"])
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    loops = 3 if args.mode == "forward" else 1

    for l in range(loops):
        if loops > 1:
            print(f"\n>>> Forward Pass Wave {l+1}/{loops} <<<")
        for chat in CHATS:
            run_scraper(chat, TARGET_USER, args.mode, args.limit)

if __name__ == "__main__":
    main()
