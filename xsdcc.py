#!/usr/bin/python

import libxml2, sys, os
import urlparse
sys.path.append(".")
sys.setrecursionlimit(10000)
from fsm import XMLFsm, State

class switch(object):
	def __init__(self, value):
		self.value = value
		self.fall = False

	def __iter__(self):
		yield self.match
		raise StopIteration

	def match(self, *args):
		if self.fall or not args:
			return True
		elif self.value in args:
			self.fall = True
			return True
		else:
			return False

class XSCompiler:
	XSC_NS = "urn:application:xsc"
	def __init__(self):
		self.subgraphs = dict()
		self.substs = dict()
		self.Decls = {0: dict(), 1: dict(), 2: dict()}
		self.declTypes = dict(attribute=0, element=1, complexType=2, attributeGroup=0, group=1, simpleType=2)
		self.loadedSchemas = set()
		self.definitions = dict()
		self.Decls[2] = {
			"{http://www.w3.org/2001/XMLSchema}string": None,
			"{http://www.w3.org/2001/XMLSchema}double": None,
			"{http://www.w3.org/2001/XMLSchema}boolean": None,
			"{http://www.w3.org/2001/XMLSchema}integer": None,
			"{http://www.w3.org/2001/XMLSchema}positiveInteger": None,
			"{http://www.w3.org/2001/XMLSchema}nonNegativeInteger": None,
			"{http://www.w3.org/2001/XMLSchema}decimal": None,
			"{http://www.w3.org/2001/XMLSchema}dateTime": None,
			"{http://www.w3.org/2001/XMLSchema}unsignedLong": None,
			"{http://www.w3.org/2001/XMLSchema}token": None,
			"{http://www.w3.org/2001/XMLSchema}normalizedString": None
		}


	def expandQName(self, node, qname):
		prefix, localname = qname.split(":")
		if localname is None:
			prefix, localname = localname, prefix
		return "{%s}%s" % (node.searchNs(node.get_doc(), prefix).content, localname)

	def importDef(self, node, targetNamespace):
		qname = "{%s}%s" % (targetNamespace, node.prop("name"))
		self.Decls[self.declTypes[node.name]][qname] = node
#		print "Registered type %s" % qname
		subst = node.prop("substitutionGroup")
		if bool(subst):
			subst = self.expandQName(node, subst)
			if not self.substs.has_key(subst): self.substs[subst] = set()
			self.substs[subst].add(node)
#			print "  added %s as substitut for %s" % (qname, subst)

	def loadSchema(self, uri, targetNamespace = None):
		if uri in self.loadedSchemas: return
		print "Loading schema file: %s" % uri
		self.loadedSchemas.add(uri)

		doc = libxml2.readFile(uri, None, options = libxml2.XML_PARSE_NOBLANKS)
		root = doc.getRootElement()
		xpath = doc.xpathNewContext()

		result = xpath.xpathEval("/*[local-name()='schema']/*[local-name()='include' or local-name()='import']")
		for node in result:
			url = urlparse.urlparse(node.prop("schemaLocation"))
			if bool(url.scheme): continue
			loc = os.path.normpath(os.path.join(os.path.dirname(uri), url.path))
			self.loadSchema(loc, targetNamespace if node.name == "include" else None)

		if targetNamespace is None:
			targetNamespace = root.prop("targetNamespace")

		result = xpath.xpathEval("/*[local-name()='schema']/*")
		for node in result:
			if node.name not in self.declTypes: continue
			self.importDef(node, targetNamespace)

	def targetNamespace(self, node):
		return node.get_doc().getRootElement().prop("targetNamespace")
	
	@staticmethod
	def getActions(s):
		if s is None: return []
		return [x for x in s.split(" ")]

	def createContentModel(self, node, ea, la, _stack = list()):
		name = node.prop("name")
		minOccurs = node.prop("minOccurs")
		minOccurs = 1 if minOccurs is None else int(minOccurs)
		maxOccurs = node.prop("maxOccurs")
		maxOccurs = 1 if maxOccurs is None else (maxOccurs if maxOccurs == "unbounded" else int(maxOccurs))
		fsm = None
		ea.extend(self.getActions(node.prop("enter")))
		la[:0] = self.getActions(node.prop("leave"))
		print "%s: '%s' (%s, %s) [%d] / %s | %s" % (node.name, name, minOccurs, maxOccurs, len(_stack), ea, la)
		if _stack.count(node) > 0:
			print "*** recursion detected ***"
			return XMLFsm().empty()

		stack = list(_stack)
		stack.append(node)
		for case in switch(node.name):
			if case("element"):
				if node.prop("ref") is not None:
					ref = self.Decls[1][self.expandQName(node, node.prop("ref"))]
					if ref is None: raise BaseException("Referenced element not known: %s" % node.prop("ref"))
					return self.createContentModel(ref, [], [], stack).apply(ea, la).particle(minOccurs, maxOccurs)

				name = node.prop("name")
				if name is None: raise BaseException("Element requires a name")
				qname = "{%s}%s" % (self.targetNamespace(node), name)
				if self.subgraphs.has_key(qname) > 0:
					print "*** call to subgraph %s ***" % qname
					fsm = XMLFsm()
					fsm.entry = State()
					leave = State()
					fsm.entry.addTransition("%s%s" % ('!' if node.prop("abstract") == "true" else "", qname), leave)
					fsm.accepts.add(leave)
					return fsm.particle(minOccurs, maxOccurs)

				if node.prop("abstract") == "true":
					if self.substs.has_key(qname):
						content = []
						for child in self.substs[qname]:
							content.append(self.createContentModel(child, [], [], stack))
						if len(content) > 0:
							return XMLFsm().choice(content).particle(minOccurs, maxOccurs)
					return XMLFsm().empty()

				content = None
				if node.prop("type") is not None:
					typename = self.expandQName(node, node.prop("type"))
					if not self.Decls[2].has_key(typename):
						raise BaseException("Unknown type %s" % typename)
					if self.Decls[2][typename] is not None:
						content = self.createContentModel(self.Decls[2][typename], ea, la, stack)
				else:
					for child in node.children:
						if child.name in ("simpleType", "complexType"):
							content = self.createContentModel(child, ea, la, stack)
							break
				if content is None: content = XMLFsm().empty()
				return XMLFsm().element(name, content).apply(ea, la).particle(minOccurs, maxOccurs)
				break

			if case("simpleType"):
				return XMLFsm().empty()
				break

			if case("complexType"):
				content = None
				if node.children is not None:
					for child in node.children:
						if child.name in ("simpleContent", "complexContent", "group", "choice", "sequence", "all"):
							content = self.createContentModel(child, [], [], stack)
							break
				content = XMLFsm().empty() if content is None else content
				return content
				break

			if case("sequence", "choice"):
				content = []
				if node.children is not None:
					for child in node.children:
						if child.name in ("element", "group", "choice", "sequence", "any"):
							content.append(self.createContentModel(child, [], [], stack))
				if len(content) == 0:
					content = XMLFsm().empty()
				else:
					content = XMLFsm().sequence(content) if node.name == "sequence" else XMLFsm().choice(content)
				return content.apply(ea, la).particle(minOccurs, maxOccurs)
				break

			if case("complexContent"):
				content = None
				if node.children is not None:
					for child in node.children:
						if child.name in ("extension", "restriction"):
							content = self.createContentModel(child, [], [], stack)
							break
				return XMLFsm().empty() if content is None else content
				break

			if case("extension", "restriction"):
				if node.name == "extension":
					qname = self.expandQName(node, node.prop("base"))
					base = self.Decls[2][qname]
					baseContent = XMLFsm().empty() if base is None else self.createContentModel(base, [], [], stack)
				else:
					baseContent = XMLFsm().empty()
				content = None
				if node.children is not None:
					for child in node.children:
						if child.name in ("group", "choice", "sequence"):
							content = self.createContentModel(child, [], [], stack)
							break
				if content is None:
					fsm = baseContent
				else:
					fsm = baseContent.concat(content)
#					if node.prop("base") == "se:SymbolizerType":
#						print "**********"
##						baseContent.dump()
#						content.dump()
#						fsm.dump()
				return fsm
				break

			if case("any"):
				return XMLFsm().element("*", XMLFsm.empty()).particle(minOccurs, maxOccurs)
				break

			if case():
				raise BaseException("Unknown schema object: %s" % node.name)
		return fsm

cc = XSCompiler()
cc.loadSchema(os.path.normpath(sys.argv[1]))
cc.subgraphs.update({
	"{http://www.opengis.net/ogc}expression": None,
	"{http://www.opengis.net/se}Graphic": None,
	"{http://www.opengis.net/gml}_Geometry": None
})
nfa = cc.createContentModel(cc.Decls[1]["{http://www.opengis.net/se}LineSymbolizer"], [], [])
nfa.dump()
dfa = nfa.determinize().minimize().dump()
#dfa.dump2()
