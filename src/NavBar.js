import React from 'react';
import { Container,Navbar,Nav,NavDropdown } from 'react-bootstrap'

export default function navBar(props) {
    return (
<Container>
<Navbar collapseOnSelect bg="dark" variant="dark" expand="lg" fixed="top">
  <Navbar.Brand href="#home">{props.appTitle}</Navbar.Brand>
  <Navbar.Toggle aria-controls="responsive-navbar-nav" />
  <Navbar.Collapse id="responsive-navbar-nav">
    <Nav className="mr-auto">
      <Nav.Link href="#home">Home</Nav.Link>
      <Nav.Link href="#link">Link</Nav.Link>      
    </Nav>
    <Nav>      
      <NavDropdown title="Help" id="basic-nav-dropdown">
        <NavDropdown.Item href="https://github.com/Phazeshift/smokerpi">About</NavDropdown.Item>        
      </NavDropdown>
    </Nav>
    </Navbar.Collapse>
</Navbar>
</Container>
);
}
