#!/bin/sh
# Wait For OpenStack Swift Available (TCP 8080)
while ! swift -A http://swift:8080/auth/v1.0 -U test:tester -K testing stat test >/dev/null 2>&1; do # DevSkim: ignore DS137138
	sleep 1
done

# shellcheck source=/dev/null
. "${VIRTUAL_ENV}"/bin/activate
python3 "${SCRIPT}"
