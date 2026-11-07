# GIGA OSINT

## Instalasi Termux & Ubuntu

**Termux**
```bash
pkg update && pkg upgrade -y
pkg install python git -y
git clone https://github.com/USERNAME/gs.git
cd gs
python giga_osint.py
```

**Ubuntu**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv git -y
git clone https://github.com/USERNAME/gs.git
cd gs
python3 -m venv .venv
source .venv/bin/activate
python3 giga_osint.py
```
