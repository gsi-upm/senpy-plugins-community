NAME:=meaningcloud
VERSIONFILE:=VERSION
IMAGENAME:=registry.cluster.gsi.dit.upm.es/senpy/sentiment-meaningcloud

include .makefiles/base.mk
include .makefiles/k8s.mk
include .makefiles/python.mk
