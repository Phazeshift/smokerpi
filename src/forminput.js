import React from 'react';
import PropTypes from 'prop-types';
import { Form } from 'react-bootstrap';

export const FormInput = ({
        name,
        type,
        placeholder,
        onChange,
        className,
        value,
        error,
        children,
        label,
        ...props
      }) => {
        
        return (
          <Form.Group>
            <Form.Label htmlFor={name}>{label}</Form.Label>
            <Form.Control
              id={name}
              name={name}
              type={type}
              placeholder={placeholder}
              onChange={onChange}
              value={value}
              className={className}
              style={error && {border: 'solid 1px red'}}
            />
            { error && <p>{ error }</p>}
          </Form.Group>
        )
      }
      
      FormInput.defaultProps = {
        type: "text",
        className: ""
      }
      
      FormInput.propTypes = {
        name: PropTypes.string.isRequired,        
        placeholder: PropTypes.string.isRequired,
        type: PropTypes.oneOf(['text', 'number', 'password']),
        className: PropTypes.string,
        value: PropTypes.any,
        onChange: PropTypes.func.isRequired
      }