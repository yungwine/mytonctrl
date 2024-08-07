#!/bin/bash
set -e

# Проверить sudo
if [ "$(id -u)" != "0" ]; then
	echo "Please run script as root"
	exit 1
fi

# Get arguments
while getopts u: flag
do
	case "${flag}" in
		u) user=${OPTARG};;
	esac
done

# Цвета
COLOR='\033[92m'
ENDC='\033[0m'

# Установка компонентов python3
echo -e "${COLOR}[1/4]${ENDC} Installing required packages"
pip3 install pipenv==2022.3.28

# Клонирование репозиториев с github.com
echo -e "${COLOR}[2/4]${ENDC} Cloning github repository"
cd /usr/src
rm -rf pytonv3
#git clone https://github.com/EmelyanenkoK/pytonv3
git clone https://github.com/igroman787/pytonv3

# Установка модуля
cd /usr/src/pytonv3
python3 setup.py install

# Скомпилировать недостающий бинарник
cd /usr/bin/ton && make tonlibjson

# Прописать автозагрузку
echo -e "${COLOR}[3/4]${ENDC} Add to startup"
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
echo "Script dir: ${SCRIPT_DIR}"
${SCRIPT_DIR}/add2systemd -n pytonv3 -s "/usr/bin/python3 -m pyTON --liteserverconfig /usr/bin/ton/local.config.json --libtonlibjson /usr/bin/ton/tonlib/libtonlibjson.so" -u ${user} -g ${user}
systemctl restart pytonv3

# Конец
echo -e "${COLOR}[4/4]${ENDC} pyTONv3 installation complete"
exit 0
