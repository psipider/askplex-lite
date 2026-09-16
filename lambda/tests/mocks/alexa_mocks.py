"""
Mock classes for Alexa SDK components to enable local testing without deployment.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ValueWrapper:
    """Mock wrapper for the value object."""
    name: str
    id: Optional[str] = None


@dataclass
class Value:
    """Mock Value class for entity resolution."""
    value: ValueWrapper


@dataclass
class ResolutionsPerAuthority:
    """Mock ResolutionsPerAuthority class for entity resolution."""
    values: list[Value]
    authority: Optional[str] = None
    status: Optional[Dict] = None


@dataclass
class Resolutions:
    """Mock Resolutions class for entity resolution."""
    resolutions_per_authority: list[ResolutionsPerAuthority]


@dataclass
class Slot:
    """Mock Slot class for Alexa SDK."""
    value: str
    name: Optional[str] = None
    resolutions: Optional[Resolutions] = None


@dataclass
class Intent:
    """Mock Intent class for Alexa SDK."""
    name: str
    slots: Dict[str, Slot] = field(default_factory=dict)
    confirmation_status: Optional[str] = None


@dataclass
class Request:
    """Mock Request class for Alexa SDK."""
    request_id: str
    type: str
    intent: Optional[Intent] = None
    locale: str = "en-US"
    timestamp: Optional[str] = None
    reason: Optional[str] = None


@dataclass
class System:
    """Mock System class for Alexa SDK."""
    device: Optional['Device'] = None
    application: Optional['Application'] = None
    user: Optional['User'] = None
    api_endpoint: Optional[str] = None
    api_access_token: Optional[str] = None


@dataclass
class Device:
    """Mock Device class for Alexa SDK."""
    device_id: str = "test-device-id"
    supported_interfaces: Dict = field(default_factory=lambda: {"audio_player": {}})


@dataclass
class Application:
    """Mock Application class for Alexa SDK."""
    application_id: str = "test-application-id"


@dataclass
class User:
    """Mock User class for Alexa SDK."""
    user_id: str = "test-user-id"
    access_token: Optional[str] = None
    permissions: Optional[Dict] = None


@dataclass
class Context:
    """Mock Context class for Alexa SDK."""
    system: System
    audio_player: Optional[Dict] = None
    viewport: Optional[Dict] = None


@dataclass
class RequestEnvelope:
    """Mock RequestEnvelope class for Alexa SDK."""
    request: Request
    context: Context
    version: str = "1.0"


class MockResponseBuilder:
    """Mock ResponseBuilder class for Alexa SDK."""
    
    def __init__(self):
        self._speak_output = None
        self._ask_output = None
        self._directives = []
        self._should_end_session = False
        self._response = None
    
    def speak(self, text: str) -> 'MockResponseBuilder':
        """Add speech output."""
        self._speak_output = text
        return self
    
    def ask(self, text: str = None) -> 'MockResponseBuilder':
        """Add reprompt output."""
        self._ask_output = text or self._speak_output
        return self
    
    def add_directive(self, directive) -> 'MockResponseBuilder':
        """Add a directive."""
        self._directives.append(directive)
        return self
    
    def set_should_end_session(self, should_end: bool) -> 'MockResponseBuilder':
        """Set whether session should end."""
        self._should_end_session = should_end
        return self
    
    @property
    def response(self) -> 'MockResponse':
        """Get the response object."""
        if self._response is None:
            self._response = MockResponse(
                output_speech=self._speak_output,
                reprompt=self._ask_output,
                directives=self._directives,
                should_end_session=self._should_end_session
            )
        return self._response


@dataclass
class MockResponse:
    """Mock Response class for Alexa SDK."""
    output_speech: Optional[str] = None
    reprompt: Optional[str] = None
    directives: list = field(default_factory=list)
    should_end_session: bool = False


class MockAttributesManager:
    """Mock AttributesManager class for Alexa SDK."""
    
    def __init__(self):
        self._request_attributes: Dict[str, Any] = {}
        self._session_attributes: Dict[str, Any] = {}
        self._persistent_attributes: Dict[str, Any] = {}
    
    @property
    def request_attributes(self) -> Dict[str, Any]:
        """Get request attributes."""
        return self._request_attributes
    
    @property
    def session_attributes(self) -> Dict[str, Any]:
        """Get session attributes."""
        return self._session_attributes
    
    @property
    def persistent_attributes(self) -> Dict[str, Any]:
        """Get persistent attributes."""
        return self._persistent_attributes
    
    def save_persistent_attributes(self):
        """Save persistent attributes (mock implementation)."""
        pass


class MockDirectiveService:
    """Mock DirectiveService for progressive responses."""
    
    def enqueue(self, directive_request):
        """Enqueue directive (mock implementation)."""
        pass


class MockServiceClientFactory:
    """Mock ServiceClientFactory for progressive responses."""
    
    def get_directive_service(self):
        """Get directive service (mock implementation)."""
        return MockDirectiveService()


class MockHandlerInput:
    """Mock HandlerInput class for Alexa SDK."""
    
    def __init__(self, request_envelope: RequestEnvelope):
        self._request_envelope = request_envelope
        self._attributes_manager = MockAttributesManager()
        self._response_builder = MockResponseBuilder()
        self._service_client_factory = MockServiceClientFactory()
        
        # Initialize default persistent attributes structure
        self._attributes_manager._persistent_attributes = {
            "playback_info": {
                "playlist": {},
                "play_order": [],
                "index": 0,
                "offset_in_ms": 0,
                "playback_index_changed": False,
                "next_stream_enqueued": False,
                "has_started": False,
                "playlist_name": None
            },
            "playback_setting": {
                "shuffle": False,
                "loop": False
            }
        }
    
    @property
    def request_envelope(self) -> RequestEnvelope:
        """Get request envelope."""
        return self._request_envelope
    
    @property
    def attributes_manager(self) -> MockAttributesManager:
        """Get attributes manager."""
        return self._attributes_manager
    
    @property
    def response_builder(self) -> MockResponseBuilder:
        """Get response builder."""
        return self._response_builder
    
    @property
    def service_client_factory(self) -> MockServiceClientFactory:
        """Get service client factory."""
        return self._service_client_factory
    
    def get_slot(self, slot_name: str) -> Optional[Slot]:
        """
        Get a slot value directly from the request intent.
        This provides a workaround for testing without full Alexa SDK validation.
        """
        if self._request_envelope.request.intent:
            print(self._request_envelope.request.intent.slots)
            return self._request_envelope.request.intent.slots.get(slot_name)
        return None


def create_mock_handler_input(intent_name: str, slots: Dict[str, str] = None) -> MockHandlerInput:
    """
    Create a mock HandlerInput for testing.
    
    Args:
        intent_name: Name of the intent to simulate
        slots: Dictionary of slot names and values
    
    Returns:
        MockHandlerInput instance configured with the specified intent
    """
    slot_objects = {}
    if slots:
        for slot_name, slot_value in slots.items():
            value_wrapper = ValueWrapper(name=slot_value)
            value_obj = Value(value=value_wrapper)
            resolutions_per_authority = ResolutionsPerAuthority(values=[value_obj])
            resolutions = Resolutions(resolutions_per_authority=[resolutions_per_authority])
            slot_objects[slot_name] = Slot(value=slot_value, name=slot_name, resolutions=resolutions)
    
    intent = Intent(name=intent_name, slots=slot_objects)
    request = Request(
        request_id="test-request-id",
        type="IntentRequest",
        intent=intent
    )
    
    device = Device()
    system = System(device=device)
    context = Context(system=system)
    request_envelope = RequestEnvelope(request=request, context=context)
    
    return MockHandlerInput(request_envelope)
