Feature: Download using HTTP GET requests
  Scenario: Download Google's Logo
    Given We have an HTTP download manager
    When The HTTP download manager starts to download Google's Logo
    Then It is downloaded and also called listeners