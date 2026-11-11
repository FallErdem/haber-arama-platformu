package com.erdemgural.newssearch;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;

@SpringBootTest
@Import(TestDatabaseConfiguration.class)
class NewsSearchApplicationTests {

	@Test
	void contextLoads() {
	}

}
