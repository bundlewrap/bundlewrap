
all: docset

mkdocs:
	mkdocs build

docset: mkdocs
	python bin/abs2rel.py -v build
	find build -name "*.html" -exec bin/add-dash-anchors.py {} -v \;
	mkdir -p release/Bundlewrap.docset/Contents/Resources/Documents
	cp -a build/* release/Bundlewrap.docset/Contents/Resources/Documents
	python bin/yaml2sqlite.py -v mkdocs.yml release/Bundlewrap.docset/Contents/Resources/docSet.dsidx
	cp assets/Info.plist release/Bundlewrap.docset/Contents
	cp assets/icon@2x.png release/Bundlewrap.docset/icon@2x.png
	cp assets/icon.png release/Bundlewrap.docset/icon.png

clean:
	rm -rf build release
