import React from 'react';
import { Container,Navbar,Nav,NavDropdown,NavItem } from 'react-bootstrap'
import { LinkContainer } from 'react-router-bootstrap'

export default function navBar(props) {
    return (
<Container>
<Navbar collapseOnSelect bg="dark" variant="dark" expand="lg" fixed="top">
  <Navbar.Brand>{props.appTitle}</Navbar.Brand>  
  <Navbar.Toggle aria-controls="responsive-navbar-nav" />
  <Navbar.Collapse id="responsive-navbar-nav">
    <Nav className="mr-auto">      
    <LinkContainer to="/">
        <NavItem as={Nav.Link}>Home</NavItem>
    </LinkContainer>
    <LinkContainer to="/config">
      <NavItem as={Nav.Link}>Config</NavItem>
    </LinkContainer>    
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
