APP=epicyon
VERSION=1.2

all:
debug:
source:
	rm -f *.*~ *~
	rm -f orgs/*~
	rm -f scripts/*~
	rm -rf __pycache__
	rm -f \#* \.#* src/*~
	rm -fr deb.*
	rm -f ../${APP}*.deb ../${APP}*.changes ../${APP}*.asc ../${APP}*.dsc
	cd .. && mv ${APP} ${APP}-${VERSION} && tar -zcvf ${APP}_${VERSION}.orig.tar.gz ${APP}-${VERSION}/ && mv ${APP}-${VERSION} ${APP}
clean:
	rm -f *.*~ *~
	rm -f orgs/*~
	rm -f scripts/*~
	rm -rf __pycache__
