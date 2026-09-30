import React from 'react';
import { connect } from 'react-redux';
import { Alert } from 'react-bootstrap';
import { dismissApiError } from './actions/actions';
import * as selectors from './selectors/selector';

// Shows the most recent failed API call until it is dismissed or a later call succeeds.
export const ErrorBanner = ({ error, dismiss }) =>
  error ? (
    <Alert variant="danger" dismissible onClose={dismiss} className="mt-2 mb-0">
      {error}
    </Alert>
  ) : null;

const mapStateToProps = state => ({ error: selectors.getApiError(state) });

const mapDispatchToProps = { dismiss: dismissApiError };

export default connect(mapStateToProps, mapDispatchToProps)(ErrorBanner);
