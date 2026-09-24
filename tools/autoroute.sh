#!/usr/bin/env bash
#
# autoroute.sh -- run Freerouting over a Specctra .dsn and write a .ses.
#
#   tools/autoroute.sh elec/layout/default/default.dsn [passes]
#
# KiCad makes the .dsn (File > Export > Specctra DSN...) and reads the .ses
# back (File > Import > Specctra Session...). Freerouting is the bit in the
# middle and it runs with no display at all, which is why this script exists:
# the whole loop can happen on a machine with no GUI, or in a session like the
# one that wrote this file.
#
# WHAT TO GIVE IT, AND WHAT NOT TO, is in docs/layout-walkthrough.md, step 9a.
# Read that before the first run. The short version: this board has three
# switching loops, a USB pair, an antenna keepout and 38 dome sites you cannot
# put a via under, and an autorouter knows about none of them.
#
# Java 25 or newer is required -- Freerouting 2.x is compiled to class file
# version 69. If `java -version` says 21, see the note at the bottom.
set -euo pipefail

FR_VERSION="${FR_VERSION:-2.4.1}"
FR_HOME="${FR_HOME:-$HOME/.freerouting-cli}"
JAR="$FR_HOME/freerouting-$FR_VERSION.jar"
CP_FILE="$FR_HOME/classpath.txt"

dsn="${1:-}"
passes="${2:-100}"
if [ -z "$dsn" ] || [ ! -f "$dsn" ]; then
    echo "usage: $0 <board.dsn> [passes]" >&2
    exit 2
fi
ses="${dsn%.dsn}.ses"

# --- find a Java 25 -------------------------------------------------------
# JAVA wins if it is set. Otherwise try `java`, then jdk4py, which is a whole
# JDK packaged as a Python wheel and the only route to a current Java on a
# machine that can reach PyPI but not much else.
find_java() {
    if [ -n "${JAVA:-}" ]; then echo "$JAVA"; return; fi
    for cand in java \
        "$(python3 -c 'import jdk4py,os;print(os.path.join(jdk4py.JAVA_HOME,"bin","java"))' 2>/dev/null || true)"
    do
        [ -n "$cand" ] || continue
        command -v "$cand" >/dev/null 2>&1 || [ -x "$cand" ] || continue
        v=$("$cand" -version 2>&1 | grep -oE '"[0-9]+' | head -1 | tr -d '"')
        if [ -n "$v" ] && [ "$v" -ge 25 ]; then echo "$cand"; return; fi
    done
}

JAVA_BIN="$(find_java || true)"
if [ -z "$JAVA_BIN" ]; then
    cat >&2 <<'MSG'
No Java 25 or newer found.

  macOS, if you have Homebrew:   brew install openjdk
  anywhere with pip:             pip install jdk4py
                                 (then run this script again -- it finds it)
  or set JAVA=/path/to/bin/java

Freerouting 2.x is built for Java 25. A Java 21 runtime fails with
"UnsupportedClassVersionError ... class file version 69.0", which is what that
message means.
MSG
    exit 1
fi

# --- fetch Freerouting and its dependencies, once ------------------------
# From Maven Central rather than GitHub: the jar there is the same build, and
# a plain HTTPS GET works in more places than a release-asset redirect does.
if [ ! -f "$JAR" ] || [ ! -s "$CP_FILE" ]; then
    echo "fetching Freerouting $FR_VERSION into $FR_HOME"
    mkdir -p "$FR_HOME"
    base="https://repo1.maven.org/maven2/app/freerouting/freerouting/$FR_VERSION"
    for attempt in 1 2 3 4 5; do
        code=$(curl -fsS -m 300 -o "$JAR" -w "%{http_code}" "$base/freerouting-$FR_VERSION.jar" || echo fail)
        [ "$code" = "200" ] && break
        echo "  attempt $attempt: $code, retrying"      # Central rate-limits
        sleep $((attempt * 15))
    done
    [ -s "$JAR" ] || { echo "could not download the jar" >&2; exit 1; }

    # The published jar is the library, not a fat jar -- no Main-Class and no
    # bundled dependencies -- so Maven resolves the tree into a classpath.
    command -v mvn >/dev/null || { echo "need maven to resolve dependencies" >&2; exit 1; }
    tmp="$(mktemp -d)"
    cat > "$tmp/pom.xml" <<EOF
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>local</groupId><artifactId>frdeps</artifactId><version>1</version>
  <dependencies>
    <dependency>
      <groupId>app.freerouting</groupId>
      <artifactId>freerouting</artifactId>
      <version>$FR_VERSION</version>
    </dependency>
  </dependencies>
</project>
EOF
    (cd "$tmp" && mvn -B -q dependency:build-classpath -Dmdep.outputFile="$CP_FILE")
    rm -rf "$tmp"
fi

# --- route ----------------------------------------------------------------
# gui.enabled=false stops it looking for a screen; disable_analytics stops it
# posting to its own telemetry endpoint, which is not this board's business.
echo "routing $dsn with up to $passes passes"
FREEROUTING__GUI__ENABLED=false \
FREEROUTING__USAGE_AND_DIAGNOSTIC_DATA__DISABLE_ANALYTICS=true \
"$JAVA_BIN" -Djava.awt.headless=true \
    -cp "$JAR:$(cat "$CP_FILE")" \
    app.freerouting.Freerouting \
    -de "$dsn" -do "$ses" -mp "$passes" 2>&1 \
  | grep -vE "^Picked up|GUI is disabled" \
  | tee "${dsn%.dsn}.autoroute.log"

echo
echo "--- what to look at ---"
grep -E "Auto-routing stage completed|Optimization stage completed|finished with state" \
     "${dsn%.dsn}.autoroute.log" || true
echo
echo "wrote $ses"
echo "UNROUTED AND VIOLATIONS ARE THE TWO NUMBERS THAT MATTER. A run that ends"
echo "with unrouted nets is telling you something about the placement, not"
echo "about the router. See docs/layout-walkthrough.md step 9a."
