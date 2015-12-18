'''
Created on May 26, 2014

@author: andreamonacchi
'''

from rdflib.graph import Graph
from rdflib.namespace import Namespace, DC, XSD, FOAF
from rdflib.extras.describer import Describer

# Create a namespace for the appliance ontology
APPS = Namespace('http://www.monergy-project.eu/ontologies/appliances.owl#')

"""
Managent of device signatures
"""
class Signature:
    def __init__(self):
        pass
    
    def to_rdf(self):
        pass

class ModelBasedDeviceSignature(Signature):
    def __init__(self):
        self.states = []
        
    def add_state(self, state):
        self.states.append(state)
        
    def to_rdf(self, base_uri, service_name):
        g = Graph()
        g.bind("base", base_uri)
        s = Describer(g,
                      about="signatures/"+service_name+"#ModelBasedDeviceSignature",
                      base=base_uri)
        
        for state in self.states:
            state_graph, state_URI = state.to_rdf(base_uri, service_name)
            s.rel(APPS.hasStateModel, state_URI)
            g += state_graph
        return g, s._current()
            

class PermanentDeviceSignature(Signature):
    def __init__(self, peakPower):
        self.peakPower = peakPower

class State:
    def __init__(self, order, peak_power, state_duration, power_tolerance=0, delay_sensitivity=0, interruption_sensitivity=0):
        self.order = order
        self.peakPower = peak_power
        self.power_tolerance = power_tolerance
        self.state_duration = state_duration
        self.delay_sensitivity = delay_sensitivity
        self.interruption_sensitivity = interruption_sensitivity
    
    def to_rdf(self, base_uri, service_name):
        g = Graph()
        g.bind("base", base_uri)
        t = Describer(g,
                      about="states/"+service_name+"_"+str(self.order)+"#State",
                      base=base_uri)
        t.rdftype(APPS.State)
        t.value(APPS.hasOrder, self.order)
        t.value(APPS.hasPeakPower, self.peakPower)
        t.value(APPS.hasWorkingPowerTolerance, self.power_tolerance)
        t.value(APPS.hasStateDuration, self.state_duration)
        t.value(APPS.hasDelaySensitivity, self.delay_sensitivity)
        t.value(APPS.hasInterruptionSensitivity, self.interruption_sensitivity)
        return g, t._current()
        

class Status:
    def __init__(self, status, current_state):
        self.status = status
        # Status = {OFF, ON, PAUSED}
        self.current_state = current_state
        self.elapsed_duration = 0
        #self.unix_start_time =    # TODO: 
        
    def set_status(self, status):
        self.status = status
        
    def update_elapsed_duration(self, duration):
        self.elapsed_duration = duration
        
class Transition:
    def __init__(self, nextObservation, transitionProbability=0.5):
        self.nextObservation = nextObservation
        self.transitionProbability = transitionProbability
        
        
"""
Definition of services provided by smart appliances
"""
class Service:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        
class PhysicalService(Service):
    def __init__(self, name, description, signature, status, consumption):
        Service.__init__(self, name, description)
        ###
        self.signature = signature
        self.status = status
        self.consumption = consumption
    
    def to_rdf(self, base_uri, appliance):
        # retrieve information from the service
        g = Graph()
        g.bind("base", base_uri)
        s = Describer(g,
                      about="services/"+appliance+"_"+self.name+"#PhysicalService",
                      base=base_uri)
        s.rdftype(APPS.PhysicalService)
        s.value(APPS.hasServiceName, self.name)
        s.value(APPS.hasDescription, self.description)
        s.value(APPS.hasConsumption, self.consumption)
        # retrieve the signature for the service
        signature_graph, signature_uri = self.signature.to_rdf(base_uri, appliance)
        s.rel(APPS.hasSignature, signature_uri)
        g += signature_graph
        return g, s._current()
        
        
class VirtualService(Service):
    def __init__(self, name, description, machine_readable_interface):
        Service.__init__(self, name, description)
        ###
        self.interface_location = machine_readable_interface
        
    def to_rdf(self, base_uri, appliance):
        g = Graph()
        g.bind("base", base_uri)
        s = Describer(g,
                      about="services/"+appliance+"_"+self.name+"#VirtualService",
                      base=base_uri)
        s.value(APPS.hasServiceName, self.name)
        s.value(APPS.hasDescription, self.description)
        s.value(APPS.hasM2MInterfaceLocation, self.interface_location)
        return g, s._current()
        
class SmartService(PhysicalService, VirtualService):
    def __init__(self, name, description, signature, status, consumption, machine_readable_interface):
        PhysicalService.__init__(self, name, description, signature, status, consumption)
        VirtualService.__init__(self, name, description, machine_readable_interface)
    
    def to_rdf(self, base_uri, appliance):
        g = Graph()
        g.bind("base", base_uri)
        s = Describer(g,
                      about="services/"+appliance+"_"+self.name+"#SmartService",
                      base=base_uri)
        s.value(APPS.hasServiceName, self.name)
        s.value(APPS.hasDescription, self.description)
        s.value(APPS.hasM2MInterfaceLocation, self.interface_location)
        return g, s._current()

"""
Appliance type
"""
class ApplianceType:
    def __init__(self, type):
        self.type = type
        
    def to_rdf(self, base_uri):
        g = Graph()
        g.bind("base", base_uri)
        t = Describer(g,
                      about="types/"+self.type+"#ApplianceType",
                      base=base_uri)
        t.rdftype(APPS.ApplianceType)
        return g

"""
Appliances
"""
class Appliance:
    def __init__(self):
        import hashlib
        import time
        self.progressive_id = hashlib.sha256(str(time.time())).hexdigest()
        self.energy_rating = "UnknownRating"
        self.manufacturer = "UnknownManufacturer"
        self.manufacturer_product_id = "UnknownModel"
        self.type = "Unknown"
        self.is_controllable = False
        self.is_user_driven = False
        
    def get_appliance_id(self):
        return self.progressive_id      
    
    def to_rdf(self, base_uri):
        graph = Graph()
        graph.bind("base", base_uri)
        d = Describer(graph,
                      # using "/appliances/"+self.get_appliance_id()+"#Appliance" we get the first-level namespace domain
                      about="appliances/"+self.get_appliance_id()+"#Appliance",
                      base=base_uri)
        d.rdftype(APPS.Appliance)
        d.value(APPS.hasManufacturer, self.manufacturer)
        d.value(APPS.hasManufacturerProductID, self.manufacturer_product_id)
        if isinstance(self.energy_rating, str):
            d.value(APPS.hasEnergyClass, self.energy_rating)
        else:
            d.rel(APPS.hasEnergyClass, self.energy_rating)
        d.rel(APPS.hasType, self.type)
        return graph, d
    
class SmartAppliance(Appliance):
    def __init__(self):
        # Call parent's constructor
        Appliance.__init__(self)
        self.is_controllable = False
        
        self.implemented_M2M_technologies = []
        # Services provided by the PROFILED device
        self.hasPhysicalService = []
        self.hasVirtualService = []
        self.hasSmartService = []
    
    def set_appliance_attributes(self,
                                 manufacturer,
                                 product_id,
                                 type,
                                 is_user_driven):
        self.manufacturer = str(manufacturer)
        self.manufacturer_product_id = str(product_id)
        self.type = str(type)
        self.is_user_driven = is_user_driven
        
    def add_physical_service(self, service):
        """
        A physical service describes the operation of an electrical device
        """
        self.hasPhysicalService.append(service)
    
    def add_virtual_service(self, service):
        """
        A virtual service provides a M2M interface to GET information from an electrical device
        """
        self.hasVirtualService.append(service)
    
    def add_smart_service(self, service):
        """
        A smart service provides a M2M interface both to GET information and to CONTROL an electrical device
        """
        # the device is definetely controllable
        self.is_controllable = True
        self.hasSmartService.append(service)
    
    def add_M2M_technology(self, technology):
        self.implemented_M2M_technologies.append(technology)
        
    def to_rdf(self, base_uri):
        # Get basic graph from the parent
        graph, device = Appliance.to_rdf(self, base_uri)
        for technology in self.implemented_M2M_technologies:
            device.value(APPS.implementsM2MTechnology, technology)
        device.value(APPS.isControllable, self.is_controllable)
        device.value(APPS.isUserDriven, self.is_user_driven)
        # add all implemented services
        for service in self.hasPhysicalService:
            service_graph, service_uri = service.to_rdf(base_uri, self.get_appliance_id())
            device.rel(APPS.hasService, service_uri)
            graph += service_graph
        return graph