all:	compile clean tags minify

dist:	version clean minify
	rm -rf build
	mkdir build
	tar -czvf build/sheltermanager3-`cat VERSION`-src.tar.gz AUTHORS changelog COPYING src README
	cd installers/deb && ./makedeb.sh && mv *.deb ../../build

distwin32: dist
	cd installers/win32 && ./make.sh && mv sheltermanager*exe ../../build/sheltermanager3-`cat ../../VERSION`-win32.exe

tags:
	@echo "[tags] ============================"
	rm -f tags
	ctags -f tags src/*.py

cscope:
	@echo "[cscope] ==========================="
	find . -name '*.py' > cscope.files
	find . -name '*.psp' >> cscope.files
	cscope -b -q -k

clean:
	@echo "[clean] ============================"
	rm -f cscope*
	rm -f src/*.pyc
	rm -f src/locale/*.pyc

version:
	# Include me in any release target to stamp the 
	# build date
	@echo "[version] =========================="
	sed "s/^VERSION =.*/VERSION = \"`cat VERSION` [`date`]\"/" src/i18n.py > i18ndt.py
	sed "s/^BUILD =.*/BUILD = \"`date +%m%d%H%M`\"/" i18ndt.py > i18njs.py
	rm -f i18ndt.py
	mv -f i18njs.py src/i18n.py
	cp changelog src/static/pages/changelog.txt

minify:
	# Generate minified versions of all javascript in min folder
	@echo "[minify] ============================="
	mkdir -p src/static/js/min
	for i in src/static/js/*.js; do echo $$i; cat $$i | jsmin/jsmin > src/static/js/min/`basename $$i .js`.min.js; done

compile: compilejs compilepy

compilejs:
	@echo "[compile javascript] ================="
	cd jslint && ./run.py

compilepy:
	@echo "[compile python] ====================="
	# 800 lines per method, 25 returns, 20 args, 60 locals
	pychecker -L 800 -R 25 -J 20 -K 60 -j -b al,email,httplib,multiprocessing,threading src/*.py

smcomstable: version clean minify
	@echo "[smcom stable] ========================="
	rsync --exclude '*.pyc' --delete -r src/* root@rawsoaa2.miniserver.com:/usr/local/lib/asm_stable.new
	ssh root@rawsoaa2.miniserver.com "/root/sheltermanager_update_asm_stable.sh"

smcomdev: version clean minify
	@echo "[smcom dev] ========================="
	rsync --exclude '*.pyc' --delete -r src/* root@rawsoaa2.miniserver.com:/usr/local/lib/asm_dev.new
	ssh root@rawsoaa2.miniserver.com "/root/sheltermanager_update_asm_dev.sh"

smcom: smcomdev

pot:
	@echo "[template] ========================="
	python po/extract_strings.py > po/asm.pot

translation:
	@echo "[translation] ======================"
	cd po && ./po_to_python.py
	mv po/locale*py src/locale

icons:
	@echo "[icons] ==========================="
	cd src/static/images/icons && rm -f asm-icon.png
	cd src/static/images/icons && ./z_makesprite.sh
	mv src/static/images/icons/asm-icon.css src/static/css
	rm -f src/static/images/icons/test.html

test: version
	@echo "[test] ========================="
	cd src && python code.py 5000

tests:
	@echo "[tests] ========================"
	cd test && python suite.py
	rm -f test/*.pyc

testsdb:
	@echo "[testsdb] ========================"
	mysql -u root -proot -e "DROP DATABASE IF EXISTS asmunittest"
	mysql -u root -proot -e "CREATE DATABASE asmunittest"
	cd src && python cron.py maint_db_install MYSQL localhost 3306 root root asmunittest asmunittest

deps:
	@echo "[deps] ========================="
	apt-get install python-webpy
