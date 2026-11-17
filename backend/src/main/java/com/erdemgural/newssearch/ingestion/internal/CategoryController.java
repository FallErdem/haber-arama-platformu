package com.erdemgural.newssearch.ingestion.internal;

import com.erdemgural.newssearch.web.ListResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/categories")
class CategoryController {

    private final CategoryRepository categoryRepository;

    CategoryController(CategoryRepository categoryRepository) {
        this.categoryRepository = categoryRepository;
    }

    /** Arama ekranındaki kategori filtresinin seçenekleri. */
    @GetMapping
    ListResponse<CategoryResponse> list() {
        return new ListResponse<>(categoryRepository.findAll());
    }
}
