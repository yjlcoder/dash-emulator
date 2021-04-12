Feature: Parse MPD files

  Scenario: Parse a simple MPD file
    Given We have the MPD file content
    When nothing
    Then The MPD gets parsed right

  Scenario: Parse a simple AdaptationSet
    Given We have the XML tree of an AdaptationSet
    When nothing
    Then The AdaptationSet gets parsed right

  Scenario: Parse a simple Representation
    Given We have the XML tree of a representation
    When nothing
    Then The Representation gets parsed right