Feature: Estimate the bandwidth correctly

  Scenario: Estimate the bandwidth when there's no change
    Given We have a default bandwidth meter
    When the transmission hasn't started
    Then The bandwidth should be initial bandwidth

  Scenario: Estimate a mock bandwidth profile
    Given We have a default bandwidth meter
    When The transmission complete
    Then the bandwidth should be estimated correctly
    Then the listener should be triggered

  Scenario: Estimate a mock bandwidth profile with more than one transmissions
    Given We have a default bandwidth meter
    When The two transmissions complete
    Then The bandwidth should be estimated correctly for 2 transmissions