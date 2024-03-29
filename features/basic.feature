Feature: basic peaq blockchain test

  Scenario: Multisig test
     Given Use the Alice keypair
       and Use the Bob keypair
       and Create a multisig wallet from Alice and Bob
       and Deposit random token to multisig wallet from Alice
       and Store the bob balance
       and Send the transfer proposal to Bob from Alice
      When Approve the transfer proposal by Bob
      Then Check the token back to Bob

  Scenario: Block generation time test
      When Get all block creation time
      Then Check block create time
