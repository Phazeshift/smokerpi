import React from 'react';
import { Form } from 'react-bootstrap';

export const FormInput = ({
        name,
        type = 'text',
        placeholder,
        onChange,
        className = '',
        disabled,
        value,
        error,
        children,
        label,
        ...props
      }) => {
        
        return (
          <Form.Group className="mb-3">
            <Form.Label htmlFor={name}>{label}</Form.Label>
            <Form.Control
              id={name}
              name={name}
              type={type}
              placeholder={placeholder}
              onChange={onChange}
              value={value}
              className={className}
              disabled={disabled}
              style={error && {border: 'solid 1px red'}}
            />
            { error && <p>{ error }</p>}
          </Form.Group>
        )
      }
