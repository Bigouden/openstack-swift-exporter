#!/bin/sh
# Wait For OpenStack Swift Available (TCP 8080)
while ! nc -vz -w 1 swift 8080 >/dev/null 2>&1; do
	sleep 1
done

# shellcheck source=/dev/null
. "${VIRTUAL_ENV}"/bin/activate
python3 "${SCRIPT}"
