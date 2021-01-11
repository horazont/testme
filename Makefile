scss_files = $(filter-out testme/scss/_%.scss,$(wildcard testme/scss/*.scss))
scss_includes = $(filter testme/scss/_%.scss,$(wildcard testme/scss/*.scss))
generated_css_files = $(patsubst testme/scss/%.scss,testme/static/css/%.css,$(scss_files))
images = $(wildcard docker/*.Dockerfile)
image_targets = $(patsubst docker/%.Dockerfile,%-image,$(images))
repository = testme

PYTHON3 ?= python3
SCSSC ?= $(PYTHON3) -m scss --load-path testme/scss/

all: build_css images

images: $(image_targets)

$(image_targets): %-image: docker/%.Dockerfile
	docker build -t $(repository)/$(patsubst %-image,%,$@):latest -f docker/$(patsubst %-image,%,$@).Dockerfile .

build_css: $(generated_css_files)

$(generated_css_files): testme/static/css/%.css: testme/scss/%.scss $(scss_includes)
	mkdir -p testme/static/css/
	$(SCSSC) -o "$@" "$<"

clean:
	rm -f $(generated_css_files)

.PHONY: build_css clean images testssl-image coordinator-image web-image
