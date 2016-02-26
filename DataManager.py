'''
Created on May 26, 2014

@author: andreamonacchi
'''
import time
import sys
import web
import threading
import rdflib
from rdflib.graph import Graph
from rdflib.namespace import Namespace, DC, XSD, FOAF
from rdflib.extras.describer import Describer
from DataModel import Appliance, ApplianceType, SmartAppliance, State, Status, ModelBasedDeviceSignature, PhysicalService


shared_file = "graph.rdf"

# ---------------- Webserver ----------------
urls = (
  '/', 'index',
)

class index:
    def GET(self):
        #return gateway.get_KB_size()
        return """
                <div align="center">Welcome on the HEMS KB, this page allows you to run SPARQL queries</div>
                <div align="center">
                    <form name="query_form" action="/" method="post">
                        <textarea id="query_input" rows="20" cols="80" name="query">
PREFIX apps: <http://www.monergy-project.eu/ontologies/appliances.owl#>
SELECT DISTINCT ?a ?atype ?bname
WHERE {
?a apps:hasService ?b .
?a apps:hasType ?atype .
?b apps:hasServiceName ?bname .
}
                        </textarea><br>
                        <input id="submit_button" type="submit" value="Submit">
                    </form>
                </div>
                <div align="center">2014 - Andrea Monacchi</div>
                """

    def POST(self):
        # web.data() # returns the form raw data
        data = web.input(query="")
        g = rdflib.Graph()
        g.parse(shared_file, format="n3") # make a copy of the current graph status (a DBMS should be used in future)
        qres = g.query(data.query)
        result = ""
        for row in qres:
            result += "<ul>"
            for r in row:
                result += "<li>"+r+"</li>"
            result += "</ul></br>"
        return "<html><body>"+result+"</body></html>"
        # Create an instance of rdflib to get the current graph of the KB
        # Pass the sparql query and return the result as triples in json
# -------------------------------------------



# Create a namespace for the appliance ontology
APPS = Namespace('http://www.monergy-project.eu/ontologies/appliances.owl#')        

class DataManager:
    """
    The data manager implements the data layer: 
        provides a uniform SPARQL interface, 
        manages device profiles, 
        exploits load disaggregation information to integrate it in the KB
    """
    def __init__(self, house_id):
        # create a namespace for the knowledge base
        self.namespace = Namespace("http://www.monergy-project.eu/houses/"+house_id+"/")
        # Create a RDF graph
        self.g = rdflib.Graph()
        #self.g = rdflib.Graph(store='Sleepycat')
        #self.g.open('RDFTripleStore', create = True)
        
        self.g.bind("base", self.namespace)
        self.g.bind("apps", APPS)
        # attributes
        self.ID = 0 # number of managed devices
        
    def release_resources(self):
        pass
        #self.g.close() # used for non-memory-based triple stores
    
    # SPARQL query interface (for applications)
    def query(self, query, format=None):
        result = self.g.query(query)        
        if format is not None:
            return result.serialize(format=format)
        else:
            return result
    
    def add_appliance(self, appliance):
        #print "Adding appliance at ns "+str(self.namespace)
        self.g += appliance.to_rdf(self.namespace)
    
    def remove_appliance(self, appliance_URI):
        # remove all triples for the given device
        self.g.remove(appliance_URI, None, None)
    
    # Management of appliance datasheet
    def load_profile_from_file(self, profile):
        """ Parses a device profile from a local file """
        self.g.parse(profile)
    
    def load_profile_from_url(self,url):
        """ Parses a device profile from a remote device datasheet provider """
        self.g.parse(location=url)
        """
        print("graph has %s statements." % len(self.g))
        print("--- printing raw triples ---")
        for s, p, o in self.g:
            print((s, p, o))
        """
        
    def push_triples_to_server(self, url, apikey):
        """ pushes the triples to a remote triplestore for backup """
        pass
    
    def export_to_string(self, output_format):
        """ Exports the graph in the given format, default is XML """
        return self.g.serialize(format=output_format)
    
    def export_to_file(self, output_format, filepath):
        """ Exports the graph in the given format to a textfile """
        #print(self.g.serialize(format=output_format))
        target = open(filepath, 'w')
        target.write(self.g.serialize(format=output_format))
        target.close()
    
    def get_KB_size(self):
        return len(self.g)

class LoadDisaggregator:
    def __init__(self):
        pass
    
    def get_operating_devices(self):
        pass

class SmartGateway(threading.Thread):
    """
    Implements the load disaggregation/detection component and manages the integration of extracted information
    """
    def __init__(self, shared_file=None):
        # init thread constructor
        threading.Thread.__init__(self)
        
        self._terminate = False
        self.shared_file = shared_file
        
        # id of the household
        house_id = "12345"
        try:
            # Create a data manager for a given household (HEMS)
            self.data_manager = DataManager(house_id)
            print("Data Manager started..")
            # Create a load disaggregator driver
            self.loadDisaggregator = LoadDisaggregator()
            print("Disaggregator started..")
        except Exception as e:
            print "Exception: ", e
            sys.exit(0)
        else:
            # Start interfaces to query the KB
            self.__start_web_server_interface()
            #self.__start_query_interface() # only from CLI
            
    def get_KB_size(self):
        return self.data_manager.get_KB_size()    
        
    def __start_query_interface(self):
        threading.Thread(target=self._query_interface).start()
        
    def __start_web_server_interface(self):
        threading.Thread(target=self._query_web_interface).start()
        #self._query_web_interface()
        
    def _query_web_interface(self):
        # Start a webserver at the 8080 port
        self.app = web.application(urls, globals())
        self.app.add_processor(web.loadhook(self.load_hook))
        self.app.run()
    
    def load_hook(self):
        web.ctx.pipe = self
        
    def _query_interface(self):
        """
        Query interface:
            Available commands QUERY, END
        """
        while not self._terminate:
            input = raw_input("<QUERY format | END>#")
            if "END" in input:
                self._terminate = True
            elif "QUERY" in input and input.index("QUERY")+6 < len(input) and (input[input.index("QUERY")+6:]).strip() in ["xml", "json", "csv"]:
                format = (input[input.index("QUERY")+6:]).strip()
                
                input = query = ""  # Cool Uh?
                while not "$$" in input:
                    input = raw_input("> ")
                    query += input
                # run the query and print any error if present
                try:
                    query = query.replace('$$','')
                    #print "Format is: "+format
                    #print "Query is: "+query
                    if format is "":
                        for entry in self.query(query, format):
                            print entry
                    else:
                        print self.query(query, format)
                    
                except Exception as e:
                    print e
            else:
                pass
        
    def run(self):
        """
        Loops on the list of smart and legacy devices to check for the ones that joined or left
        """
        while not self._terminate:
            # Collect device profiles from smart appliances
            self.__collect_device_profiles_from_smart_appliances()
            # Collect device profiles from legacy devices
            self.__collect_device_profiles_from_legacy_devices()
            
            # save to memory all extracted device information
            #print self.data_manager.export_to_string('n3')
            if self.shared_file is not None:
                print("Saving to file "+self.shared_file)
                self.data_manager.export_to_file('n3', self.shared_file)
            
            time.sleep(20) # sleep for 20 secs
            
    
    def __collect_device_profiles_from_smart_appliances(self):
        # -------- Smart water kettle
        # create an appliance in the given household (to be done by a smart appliance)
        a = SmartAppliance()
        #kettle = ApplianceType("WaterKettle")
        a.set_appliance_attributes("Lakeside Labs GmbH", "WK300", APPS.WaterKettle, True)
        # Add supported technologies for the device
        a.add_M2M_technology("COAP")
        a.add_M2M_technology("DPWS")
        # define a service for the water kettle
        kettleStateZero = State(order=0, peak_power=1800.0, state_duration=60, power_tolerance=5, delay_sensitivity=0, interruption_sensitivity=0)
        kettleSignature = ModelBasedDeviceSignature()
        kettleSignature.add_state(kettleStateZero)
        kettleStatusOff = Status("Off", current_state=kettleStateZero) # TODO: we should have something like APP.StatusOFF
        waterHeatingService = PhysicalService(name="waterHeatingService", description='This service describes the operation of a water kettle', signature=kettleSignature, status=kettleStatusOff, consumption=0.03)
        a.add_physical_service(waterHeatingService)
        self.data_manager.add_appliance(a) # most important step: add the device graph to the main KB graph
        #print "KB triples: "+str(self.data_manager.get_KB_size())
        
    def __collect_device_profiles_from_legacy_devices(self):
        pass
    
    def query(self, query, format=None):
        """
        Default return format is the python SPARQLResult object, although xml, csv and json are also supported
        """
        return self.data_manager.query(query, format)
    
    def __terminate(self):
        self._terminate = True
        self.data_manager.release_resources()
    
    def _sigint_handler(self, signal, frame):
        print "Terminating"
        self.__terminate()


if __name__ == '__main__':
    gateway = SmartGateway(shared_file=shared_file)
    # starts the collection of data from smart appliances and legacy devices
    gateway.start() #.run()
    
    if False:
        print"\n\n------------------------------------------- "
        print "Query result:\n\n"
        serialized = True
        if serialized:
            qres = gateway.query("""                
                        PREFIX apps: <http://www.monergy-project.eu/ontologies/appliances.owl#>
                        SELECT DISTINCT ?a ?atype ?bname
                        WHERE {
                          ?a apps:hasService ?b .
                          ?a apps:hasType ?atype .
                          ?b apps:hasServiceName ?bname .
                        }""", format='csv')
            print qres
        else:
            qres = gateway.query("""                
                        PREFIX apps: <http://www.monergy-project.eu/ontologies/appliances.owl#>
                        SELECT DISTINCT ?a ?atype ?bname
                        WHERE {
                          ?a apps:hasService ?b .
                          ?a apps:hasType ?atype .
                          ?b apps:hasServiceName ?bname .
                        }""")
            for row in qres:
                print("URI: %s (DeviceType: %s Service provided: %s)" % row)
