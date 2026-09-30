import React from 'react';
import { Container,Navbar,Nav,NavDropdown } from 'react-bootstrap'
import { LinkContainer } from 'react-router-bootstrap'

export default function navBar(props) {
    return (
<Navbar collapseOnSelect bg="dark" variant="dark" expand="lg" fixed="top">
  <Container fluid>
    <Navbar.Brand>{props.appTitle}</Navbar.Brand>
    <Navbar.Toggle aria-controls="responsive-navbar-nav" />
    <Navbar.Collapse id="responsive-navbar-nav">
      <Nav className="me-auto">
        <LinkContainer to="/">
          <Nav.Link>Home</Nav.Link>
        </LinkContainer>
        <LinkContainer to="/config">
          <Nav.Link>Config</Nav.Link>
        </LinkContainer>
      </Nav>
      <Nav>
        <NavDropdown title="Help" id="basic-nav-dropdown" align="end">
          <NavDropdown.Item href="https://github.com/Phazeshift/smokerpi">About</NavDropdown.Item>
        </NavDropdown>
      </Nav>
    </Navbar.Collapse>
  </Container>
</Navbar>
);
}
