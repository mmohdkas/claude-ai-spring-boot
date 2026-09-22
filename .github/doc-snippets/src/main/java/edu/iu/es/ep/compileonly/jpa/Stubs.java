package edu.iu.es.ep.compileonly.jpa;

import jakarta.persistence.*;

enum OrderStatus { PENDING, ARCHIVED }

@Entity class Customer { @Id @GeneratedValue Long id; }

@Entity class OrderItem { @Id @GeneratedValue Long id; @ManyToOne Order order; }
