#!/usr/bin/python

from collections import deque
import libxml2, sys, os, re
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
			"{http://www.w3.org/2001/XMLSchema}normalizedString": None,
			"{http://www.w3.org/2001/XMLSchema}QName": None
		}
		self.namespaces = []
		self.elements = [("/")]
		self.actions = []
		self.macros = [ ("enter", 0, self.onEnter), ("leave", 0, self.onLeave) ]

	def expandQName(self, node, qname):
		try:
			prefix, localname = qname.split(":")
		except ValueError:
			localname = qname
			prefix = None
		try:
			namespace = node.searchNs(node.get_doc(), prefix).content
		except:
			namespace = ""
		return "{%s}%s" % (namespace, localname)

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
			if targetNamespace is None: targetNamespace = ""

		result = xpath.xpathEval("/*[local-name()='schema']/*")
		for node in result:
			if node.name not in self.declTypes: continue
			self.importDef(node, targetNamespace)

	def targetNamespace(self, node):
		return node.get_doc().getRootElement().prop("targetNamespace")

	def getElementId(self, namespace, localname):
		try:
			namespaceId = self.namespaces.index(namespace)
		except ValueError:
			namespaceId = len(self.namespaces)
			self.namespaces.append(namespace)

		element = (namespaceId, localname)
		try:
			elementId = self.elements.index(element)
		except ValueError:
			elementId = len(self.elements)
			self.elements.append(element)
		return elementId
	
	def getActionId(self, action):
		try:
			actionId = self.actions.index(action)
		except ValueError:
			actionId = len(self.actions)
			self.actions.append(action)
		return actionId

	def mapActions(self, actionStrings):
		return map(self.getActionId, actionStrings)
		
	def getActions(self, s):
		if s is None: return []
		l = []
		for i in re.finditer(r"\s*(\w+)\s*\(\s*((\w+\s*(,\s*\w+)*)?\s*)\)", s):
			args = "_".join([a.group(1).replace("_", "__") for a in re.finditer(r",?\s*(\w+)", i.group(2))])
			action = "%s%s%s" % (i.group(1).replace("_", "__"), "_" if len(args) > 0 else "", args)
			actionId = self.getActionId(action)
			l.append(actionId)
#		print "Action IN: %s | OUT: %s" % (s, l)
		return l

	@staticmethod
	def onEnter(self, action, ea, la):
		l = self.getActions(action)
		ea.extend(l)

	@staticmethod
	def onLeave(self, action, ea, la):
		l = self.getActions(action)
		la[:0] = l

	def addMacro(self, macro):
		for i in range(0, len(self.macros)):
			if self.macros[i][1] >= macro[1]: break
		print "Inserting macro %s with prio %d at %d" % (macro[0], macro[1], i)
		self.macros[i:i] = [macro]
		print self.macros

	def processActions(self, node, ea, la):
		for macro in self.macros:
			action = node.prop(macro[0])
			if not action: continue
			macro[2](self, action, ea, la)

	def element(self, namespace, localname, content):
		elementId = self.getElementId(namespace, localname)
		fsm = XMLFsm()
		fsm.entry = State()
		fsm.entry.addTransition(elementId, content.entry)
		leave = State()
		for state in content.accepts:
			state.addTransition(0, leave)
		fsm.accepts = set([leave])
		return fsm

	def dump2(self):
		visited = set([self.entry])
		inqueue = deque([self.entry])
		outqueue = deque()
		labels = dict()
		substs = set()
		id = 1
		labelId = 0
		while len(inqueue) > 0:
			state = inqueue.popleft()
			if state not in self.accepts:
				state.id = id
				id += 1
				outqueue.append(state)

			transitions = dict((trans.label, state.statesForLabel(trans.label)) for trans in state.transitions)
			for label, targets in transitions.iteritems():
				if not (label.startswith("/") or label.startswith('!')) and label not in labels:
					labels[label] = labelId
					labelId += 1
				elif label.startswith('!'):
					substs.add(label)
				for target in targets:
					if target not in visited:
						inqueue.append(target)
						visited.add(target)
		for state in self.accepts:
			state.id = id
			id += 1
			outqueue.append(state)
		for label in substs:
			labels[label] = labelId
			labelId += 1

		first_final = min(map(lambda x: x.id, self.accepts))
		token_list = []
		token_offset = [0]
		token_length = [0]
		target_list = [0, 0]
		target_offset = [0]

		print "first_final = %d" % first_final
		while len(outqueue) > 0:
			state = outqueue.popleft()
			onClose = 0
			nTokens = 0
			t_list = []
			token_offset.append(len(token_list))
			transitions = dict((trans.label, state.statesForLabel(trans.label)) for trans in state.transitions)
			for label, targets in transitions.iteritems():
				target = reduce(lambda x, y: x if y is None else y, targets)
				if label.startswith('/'):
					onClose = target.id
				else:
					token_list.append(labels[label])
					nTokens += 1
					t_list.append(target.id)
			target_offset.append(len(target_list))
			target_list.append(onClose)
			target_list.extend(t_list)
			target_list.append(0)		# default transition
			token_length.append(len(t_list))

		print "token_list := %s\n" % str(token_list)
		print "token_offset := %s\n" % str(token_offset)
		print "token_length := %s\n" % str(token_length)
		print "target_list := %s\n" % str(target_list)
		print "target_offset := %s\n" % str(target_offset)
		for index, token in dict(zip(labels.values(), labels.keys())).iteritems():
			print "{0, %s}" % token

	def genTables(self, dfa):
		all_states = dfa.reachables()
		states = [s for s in all_states if s not in dfa.accepts]
		states.extend([s for s in all_states if s in dfa.accepts])
		states[:0] = [State()]
		targets = []
		target_offsets = []
		tokens = []
		token_offsets = []
		token_lengths = []
		actions = []
		action_offsets = []
		for i, state in enumerate(states):
			token_offsets.append(len(tokens))
			target_offsets.append(len(targets))
			on_close = None
			local_targets = []
			local_actions = []
			local_actions_on_close = None
			for trans in state.transitions:
#				print "state %d: Token: %d -> target %d" % (i, trans.label, states.index(trans.target))
				if trans.label > 0:
					local_targets.append(states.index(trans.target))
					tokens.append(trans.label - 1)
					local_actions.append(trans.actions)
				else:
					on_close = states.index(trans.target)
					local_actions_on_close = trans.actions

			local_actions.append([])
			local_actions[:0] = [[] if local_actions_on_close is None else local_actions_on_close]
			for tactions in local_actions:
				action_offsets.append(len(actions))
				actions.append(len(tactions))	# length
				actions.extend(tactions)		# actions

			token_lengths.append(len(tokens) - token_offsets[-1])
			local_targets[:0] = [0 if on_close is None else on_close]
			local_targets.append(0)
			targets.extend(local_targets)

		print "const char * t_namespaces[] = {\n%s\n};\n" % ",\n".join(map(lambda e: "\"%s\"" % (e if e is not None else ""), self.namespaces))
		print "const element_t t_elements[] = {\n%s\n};\n" % ",\n".join(map(lambda e: "{%d, \"%s\"}" % e, self.elements[1:]))
		print "const xml_schema example_schema = {"
		print "\t\tnamespaces: t_namespaces,"
		print "\t\telements: t_elements,"
		print "\t\ttoken_names: {\n\t\t\t(const uint8_t*)((const uint8_t[]){%s})," % ", ".join(map(lambda n: "%d" % n, tokens))
		print "\t\t\t(const uint8_t*)((const uint8_t[]){%s})," % ", ".join(map(lambda n: "%d" % n, token_offsets))
		print "\t\t\t(const uint8_t*)((const uint8_t[]){%s})\n\t\t}," % ", ".join(map(lambda n: "%d" % n, token_lengths))
		print "\t\ttargets: {"
		print "\t\t\t(const uint8_t*)((const uint8_t[]){%s})," % ", ".join(map(lambda n: "%d" % n, targets))
		print "\t\t\t(const uint8_t*)((const uint8_t[]){%s})\n\t\t}," % ", ".join(map(lambda n: "%d" % n, target_offsets))
		print "\t\tfirst_final: %d," % min(map(lambda s: states.index(s), dfa.accepts))
		print "\t\tentry: %d," % states.index(dfa.entry)
		print "\tdispatch: dispatch"
		print "\t};"
		print "static const uint8_t action_list[] = {%s};" % ", ".join(map(lambda n: "%d" % n, actions))
		print "static const uint16_t action_offsets[] = {%s};" % ", ".join(map(lambda n: "%d" % n, action_offsets))
		print "enum {%s\n};" % ", ".join(map(lambda n: "\n\t%s" % n, self.actions))
		print "static const char * action_names[] = {\n%s\n};" % ",\n".join(map(lambda n: "\"%s\"" % n, self.actions))

	def dump(self, nfa):
		visited = set([nfa.entry])
		queue = deque([nfa.entry])
		nfa.entry.id = 1
		id = 2
		while len(queue) > 0:
			state = queue.popleft()
			line = ""
			line += "%s\t%s%d%s| " % ("entry:" if state == nfa.entry else "", "[" if state in nfa.accepts else " ", state.id, "]" if state in nfa.accepts else " ")
			first = True
			transitions = dict((trans.label, state.statesForLabel(trans.label)) for trans in state.transitions)
			for label, targets in transitions.iteritems():
				line += "%s%s -> " % ("" if first else ", ", self.elements[label][1] if label else "/")
				first = False
				idx = False
				for target in targets:
					if target not in visited:
						target.id = id
						id += 1
						queue.append(target)
						visited.add(target)
					line += "%s%d" % (", " if idx else "", target.id)
					idx = True
				actions = []
				for trans in state.transForLabel(label):
					actions.extend([t for t in trans.actions if t not in actions])
				idx = False
				for action in actions:
					line += "%s%s" % (", " if idx else " / ", self.actions[action])
					idx = True
			print line

	def createContentModel(self, node, ea, la, _stack = list()):
		name = node.prop("name")
		minOccurs = node.prop("minOccurs")
		minOccurs = 1 if minOccurs is None else int(minOccurs)
		maxOccurs = node.prop("maxOccurs")
		maxOccurs = 1 if maxOccurs is None else (maxOccurs if maxOccurs == "unbounded" else int(maxOccurs))
		fsm = None
		self.processActions(node, ea, la)
		print "%s%s: '%s' (%s, %s) %s | %s" % (len(_stack)* "  ", node.name, name, minOccurs, maxOccurs, [self.actions[e] for e in ea], [self.actions[a] for a in la])
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
					fsm.entry.addTransition(self.getElementId(self.targetNamespace(node), "%s%s" % ('!' if node.prop("abstract") == "true" else "", name)), leave)
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
					child = node.children
					while child is not None:
						if child.name in ("simpleType", "complexType"):
							content = self.createContentModel(child, ea, la, stack)
							break
						child = child.next
				if content is None: content = XMLFsm().empty()
				return self.element(self.targetNamespace(node), name, content).apply(ea, la).particle(minOccurs, maxOccurs)
				break

			if case("simpleType", "simpleContent"):
				return XMLFsm().empty()
				break

			if case("complexType"):
				content = None
				child = node.children
				while child is not None:
					if child.name in ("simpleContent", "complexContent", "group", "choice", "sequence", "all"):
						content = self.createContentModel(child, [], [], stack)
						break
					child = child.next
				content = XMLFsm().empty() if content is None else content
				return content
				break

			if case("sequence", "choice"):
				content = []
				child = node.children
				while child is not None:
					if child.name in ("element", "group", "choice", "sequence", "any"):
						content.append(self.createContentModel(child, [], [], stack))
					child = child.next
				if len(content) == 0:
					content = XMLFsm().empty()
				else:
					content = XMLFsm().sequence(content) if node.name == "sequence" else XMLFsm().choice(content)
				return content.apply(ea, la).particle(minOccurs, maxOccurs)
				break

			if case("complexContent"):
				content = None
				child = node.children
				while child is not None:
					if child.name in ("extension", "restriction"):
						content = self.createContentModel(child, [], [], stack)
						break
					child = child.next
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
				child = node.children
				while child is not None:
					if child.name in ("group", "choice", "sequence"):
						content = self.createContentModel(child, [], [], stack)
						break
					child = child.next
				if content is None:
					fsm = baseContent
				else:
					fsm = baseContent.concat(content)
				return fsm
				break

			if case("any"):
				fsm = XMLFsm()
				fsm.entry = State()
				leave = State()
				fsm.entry.addTransition(self.getElementId(self.targetNamespace(node), "*"), leave)
				fsm.accepts.add(leave)
				return fsm.particle(minOccurs, maxOccurs)
				break

			if case("group"):
				if node.prop("ref") is not None:
					ref = self.Decls[1][self.expandQName(node, node.prop("ref"))]
					if ref is None: raise BaseException("Referenced group not known: %s" % node.prop("ref"))
					return self.createContentModel(ref, [], [], stack).apply(ea, la).particle(minOccurs, maxOccurs)

				content = None
				child = node.children
				while child is not None:
					if child.name in ("all", "choice", "sequence"):
						content = self.createContentModel(child, [], [], stack)
						break
					child = child.next

				return XMLFsm().empty if content is None else content.apply(ea, la).particle(minOccurs, maxOccurs)

			if case():
				raise BaseException("Unknown schema object: %s" % node.name)
		return fsm

def createObject(xsc, str, ea, la):
	ea.extend(xsc.mapActions(["push_ctx", "mkctxt_" + str]))
	la[:0] = xsc.mapActions(["pop_ctx"])

if __name__ == "__main__":
	cc = XSCompiler()
	cc.addMacro(("object", -1, createObject))
	cc.loadSchema(os.path.normpath(sys.argv[1]))
	cc.subgraphs.update({
		"{http://www.opengis.net/ogc}expression": None,
		"{http://www.opengis.net/se}Graphic": None,
		"{http://www.opengis.net/ogc}Filter": None,
		"{http://www.opengis.net/se}Symbolizer": None,
		"{http://www.opengis.net/gml}_Geometry": None,
		"{http://www.opengis.net/gml}FeatureCollection": None
	})
	nfa = cc.createContentModel(cc.Decls[1]["{http://www.opengis.net/se}LineSymbolizer"], [], [])
	#nfa.dump()
	dfa = nfa.determinize().minimize()
	cc.dump(dfa)
	cc.genTables(dfa)
	#dfa.dump2()
