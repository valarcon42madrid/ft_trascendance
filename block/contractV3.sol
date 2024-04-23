// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract userDB {
    event userScore(string _login, uint8 _score, uint32 _tournamentId);
    struct user {
        string login;
        uint8 score;
        uint32 tournamentId;
    }
    mapping(string => user) public Users;
    function doUser (string memory _login, uint8 _score, uint32 _tournamentId) public {
        Users[_login] = user(_login, _score, _tournamentId);
        emit userScore(_login, _score, _tournamentId);
    }
}